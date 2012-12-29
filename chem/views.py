from cStringIO import StringIO
import zipfile
import tarfile
import os
import urllib
import re
import time

from django.shortcuts import render, redirect
from django.template import Context, RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils import simplejson
import paramiko
import misaka

from models import ErrorReport, ErrorReportForm, JobForm, LogForm, Job
import gjfwriter
import fileparser
import utils

def index(request):
    if request.GET.get("molecule"):

        func = gen_detail
        if set(",{}$") & set(request.GET.get("molecule")):
            func = gen_multi_detail

        a = {"basis" : request.GET.get("basis")}
        if a["basis"] != "B3LYP/6-31g(d)":
            b = "%s?%s" % (reverse(func, args=(request.GET.get("molecule"), )),
                urllib.urlencode(a))
            return HttpResponseRedirect(b)
        else:
            return redirect(func, request.GET.get("molecule"))
    return render(request, "chem/index.html")

def docs(request):
    a = "".join(open("README.md", "r").readlines())
    headerend = a.index("Build")
    bodystart = a.index("_"*71 + "\nNaming")
    tree = misaka.html(a[bodystart:], render_flags=misaka.HTML_TOC_TREE)
    body = misaka.html(a[bodystart:], render_flags=misaka.HTML_TOC)
    c = Context({
        "header": misaka.html(a[:headerend]),
        "toc": utils.postprocess_toc(tree, "#"),
        "docs": utils.postprocess_toc(body, 'id="'),
        })
    return render(request, "chem/docs.html", c)

def frag_index(request):
    data = (
        ["Cores" , ("CON", "TON", "TSN", "CSN", "TNN", "CNN", "CCC", "TCC")],
        ["X Groups" , (["A", "H"], ["B", "Cl"], ["C", "Br"], ["D"," CN"], ["E"," CCH"],
            ["F", "OH"], ["G", "SH"], ["H", "NH_2"], ["I", "CH_3"], ["J", "phenyl"], ["K", "TMS"],
             ["L", "OCH_3"])],
        ["Aryl Groups" , (["2", "double"], ["3", "triple"], ["4", "phenyl"], ["5", "thiophene"],
            ["6", "pyridine"], ["7", "carbazole"], ["8", "TZ"], ["9", "EDOT"])],
        ["R Groups" , (["a", "H"], ["b", "Cl"], ["c", "Br"], ["d"," CN"], ["e"," CCH"],
            ["f", "OH"], ["g", "SH"], ["h", "NH_2"], ["i", "CH_3"], ["j", "phenyl"], ["k", "TMS"],
             ["l", "OCH_3"])],
    )
    c = Context({"usable_parts": data})
    return render(request, "chem/frag_index.html", c)

def get_frag(request, frag):
    f = open("chem/data/"+frag, "r")
    response = HttpResponse(FileWrapper(f), content_type="text/plain")
    return response


###########################################################
###########################################################
# Generation Stuff
###########################################################
###########################################################


def _get_form(request, molecule):
    req = request.REQUEST
    a = dict(req)

    if a and a.keys() != ["basis"]:
        form = JobForm(req, initial=a)
    else:
        if request.user.is_authenticated():
            email = request.user.email
        else:
            email = ""
        form = JobForm(initial={"name": molecule, "email": email})
    return form

def _get_molecules_info(request, string):
    errors = []
    warnings = []
    molecules = utils.name_expansion(string)
    start = time.time()
    for mol in molecules:
        if time.time() - start > 1:
            raise ValueError("The operation has timed out.")
        try:
            gjfwriter.parse_name(mol)
            errors.append(None)
        except Exception as e:
            errors.append(e)
        warnings.append(ErrorReport.objects.filter(molecule=mol))
    return molecules, warnings, errors

def gen_detail(request, molecule):
    _, warnings, errors = _get_molecules_info(request, molecule)
    form = _get_form(request, molecule)
    basis = request.REQUEST.get("basis")
    add = "" if request.GET.get("view") else "attachment; "

    if form.is_valid():
        d = dict(form.cleaned_data)
        if request.method == "GET":
            response = HttpResponse(utils.write_job(**d), content_type="text/plain")
            response['Content-Disposition'] = add + 'filename=%s.job' % molecule
            return response
        elif request.method == "POST":
            if not request.user.is_staff:
                a = {"error" : "You must be a staff user to submit a job."}
                return HttpResponse(simplejson.dumps(a), mimetype="application/json")
            d["basis"] = basis
            d["internal"] = True
            jobid, e = utils.start_run_molecule(request.user, molecule, **d)
            a = {
                "jobid": jobid,
                "error": e,
            }
            if e is None:
                job = Job(molecule=molecule, jobid=jobid, **form.cleaned_data)
                job.save()
            return HttpResponse(simplejson.dumps(a), mimetype="application/json")

    c = Context({
        "molecule": molecule,
        "form": form,
        "known_errors": warnings[0],
        "error_message": errors[0],
        "encoded_basis": '?' + urllib.urlencode({"basis" : basis}) if basis else '',
        "basis": basis,
        })
    return render(request, "chem/molecule_detail.html", c)

def gen_multi_detail(request, string):
    try:
        molecules, warnings, errors = _get_molecules_info(request, string)
    except ValueError:
        c = Context({
            "error": "The operation timed out."
            })
        return render(request, "chem/multi_molecule.html", c)

    form = _get_form(request, "{{ name }}")
    basis = request.REQUEST.get("basis", "")
    add = "" if request.GET.get("view") else "attachment; "

    if form.is_valid():
        d = dict(form.cleaned_data)
        if request.method == "GET":
            molecule = request.REQUEST.get("molname")
            d["name"] = re.sub(r"{{\s*name\s*}}", molecule, d["name"])
            response = HttpResponse(utils.write_job(**d), content_type="text/plain")
            response['Content-Disposition'] = add + 'filename=%s.job' % molecule
            return response
        elif request.method == "POST":
            if not request.user.is_staff:
                a = {"error" : "You must be a staff user to submit a job."}
                return HttpResponse(simplejson.dumps(a), mimetype="application/json")
            a = {
                "worked": [],
                "failed": [],
            }
            for mol in molecules:
                dnew = d.copy()
                dnew["name"] = re.sub(r"{{\s*name\s*}}", mol, dnew["name"])
                jobid, e = utils.start_run_molecule(request.user, mol, basis=basis, internal=True, **dnew)
                if e is None:
                    job = Job(molecule=mol, jobid=jobid, **dnew)
                    job.save()
                    a["worked"].append((mol, jobid))
                else:
                    a["failed"].append((mol, e))
            return HttpResponse(simplejson.dumps(a), mimetype="application/json")

    c = Context({
        "molecules": zip(molecules, errors, warnings),
        "pagename": string,
        "form": form,
        "gjf": "checked",
        "basis": '?' + urllib.urlencode({"basis" : basis}) if basis else '',
        })
    return render(request, "chem/multi_molecule.html", c)

def gen_multi_detail_zip(request, string):
    basis = request.GET.get("basis")

    buff = StringIO()
    zfile = zipfile.ZipFile(buff, "w", zipfile.ZIP_DEFLATED)

    try:
        molecules, warnings, errors = _get_molecules_info(request, string)
    except ValueError:
        c = Context({
            "error": "The operation timed out."
            })
        return render(request, "chem/multi_molecule.html", c)

    if request.GET.get("job"):
        form = _get_form(request, "{{ name }}")
        if form.is_valid():
            d = dict(form.cleaned_data)
        else:
            basis = request.GET.get("basis")
            f = lambda x: 'checked' if request.GET.get(x) else ''

            c = Context({
                "molecules": zip(molecules, errors, warnings),
                "pagename": string,
                "form": form,
                "gjf": f("gjf"),
                "mol2": f("mol2"),
                "image": f("image"),
                "job": f("job"),
                "basis": '?' + urllib.urlencode({"basis" : basis}) if basis else '',
                })
            return render(request, "chem/multi_molecule.html", c)

    generrors = ''
    for name in molecules:
        try:
            out = gjfwriter.Output(name, basis)
            if request.GET.get("image"):
                f = StringIO()
                out.molecule.draw(10).save(f, "PNG")
                zfile.writestr(out.name+".png", f.getvalue())
            if request.GET.get("gjf"):
                zfile.writestr(name+".gjf", out.write_file())
            if request.GET.get("mol2"):
                zfile.writestr(name+".mol2", out.write_file(False))
            if request.GET.get("job"):
                dnew = d.copy()
                dnew["name"] = re.sub(r"{{\s*name\s*}}", name, dnew["name"])
                zfile.writestr(name+".job", utils.write_job(**dnew))

        except Exception as e:
            generrors += "%s - %s\n" % (name,  e)
    if generrors:
        zfile.writestr("errors.txt", generrors)

    zfile.close()
    buff.flush()

    ret_zip = buff.getvalue()
    buff.close()

    response = HttpResponse(ret_zip, mimetype="application/zip")
    response["Content-Disposition"] = "attachment; filename=molecules.zip"
    return response

def write_gjf(request, molecule):
    filename = molecule + ".gjf"
    basis = request.GET.get("basis")
    add = "" if request.GET.get("view") else "attachment; "

    out = gjfwriter.Output(molecule, basis)
    f = StringIO(out.write_file())
    response = HttpResponse(FileWrapper(f), content_type="text/plain")
    response['Content-Disposition'] = add + 'filename=%s.gjf' % molecule
    return response

def write_mol2(request, molecule):
    filename = molecule + ".mol2"
    add = "" if request.GET.get("view") else "attachment; "

    out = gjfwriter.Output(molecule, '')
    f = StringIO(out.write_file(False))
    response = HttpResponse(FileWrapper(f), content_type="text/plain")
    response['Content-Disposition'] = add + 'filename=%s.mol2' % molecule
    return response

def write_png(request, molecule):
    filename = molecule + ".png"
    scale = request.GET.get("scale", 10)

    out = gjfwriter.Output(molecule, '')
    response = HttpResponse(content_type="image/png")
    out.molecule.draw(int(scale)).save(response, "PNG")
    response['Content-Disposition'] = 'filename=%s.png' % molecule
    return response

def report(request, molecule):
    if request.user.is_authenticated():
        email = request.user.email
    else:
        email = ""

    if request.method == "POST":
        report = ErrorReport(molecule=molecule)
        form = ErrorReportForm(request.POST,
            instance=report,
            initial={"email" : email})
        if form.is_valid():
            form.save()
            return redirect(gen_detail, molecule)
    else:
        form = ErrorReportForm(initial={"email" : email})

    c = Context({
        "form": form,
        "molecule": molecule
        })
    return render(request, "chem/report.html", c)


###########################################################
###########################################################
# Upload Stuff
###########################################################
###########################################################


def upload_data(request):
    if request.method == "POST":
        if request.POST["option"] == "logparse":
            return parse_log(request)
        elif request.POST["option"] == "dataparse":
            return parse_data(request)
        elif request.POST["option"] == "gjfreset":
            return reset_gjf(request)
        elif request.POST["option"] == "homoorbital":
            return get_homo_orbital(request)
    form = LogForm()
    c = Context({
        "form": form,
        })
    return render(request, "chem/upload_log.html", c)

def get_homo_orbital(request):
    string = ''
    for f in utils.parse_file_list(request.FILES.getlist('myfiles')):
        string += f.name + ", " + str(fileparser.get_homo_orbital(f)) + "\n"

    f = StringIO(string)
    response = HttpResponse(FileWrapper(f), content_type="text/plain")
    return response


def parse_log(request):
    parser = fileparser.LogParser()
    for f in utils.parse_file_list(request.FILES.getlist('myfiles')):
        parser.parse_file(f)

    f = StringIO(parser.format_output())
    response = HttpResponse(FileWrapper(f), content_type="text/plain")
    return response

def parse_data(request):
    buff = StringIO()
    zfile = zipfile.ZipFile(buff, 'w', zipfile.ZIP_DEFLATED)

    n = len(list(utils.parse_file_list(request.FILES.getlist('myfiles'))))
    for f in utils.parse_file_list(request.FILES.getlist('myfiles')):
        parser = fileparser.DataParser(f)
        homolumo, gap = parser.get_graphs()

        name, _ = os.path.splitext(f.name)
        if n > 1:
            zfile.writestr(name+"/output.txt", parser.format_output())
            zfile.writestr(name+"/homolumo.eps", homolumo.getvalue())
            zfile.writestr(name+"/gap.eps", gap.getvalue())
        else:
            zfile.writestr("output.txt", parser.format_output())
            zfile.writestr("homolumo.eps", homolumo.getvalue())
            zfile.writestr("gap.eps", gap.getvalue())

    if n > 1:
        name = "output"
    zfile.close()
    buff.flush()

    ret_zip = buff.getvalue()
    buff.close()

    response = HttpResponse(ret_zip, mimetype="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s.zip" % name
    return response

def reset_gjf(request):
    buff = StringIO()
    zfile = zipfile.ZipFile(buff, 'w', zipfile.ZIP_DEFLATED)

    for f in utils.parse_file_list(request.FILES.getlist('myfiles')):
        parser = fileparser.LogReset(f)

        name, _ = os.path.splitext(f.name)
        zfile.writestr("%s.gjf" % name, parser.format_output(errors=False))

    zfile.close()
    buff.flush()

    ret_zip = buff.getvalue()
    buff.close()

    response = HttpResponse(ret_zip, mimetype="application/zip")
    response["Content-Disposition"] = "attachment; filename=output.zip"
    return response


###########################################################
###########################################################
# SSH Stuff
###########################################################
###########################################################


@login_required
def job_index(request):
    return render(request, "chem/job_index.html")

@login_required
def get_job_list(request):
    try:
        jobs = utils.get_all_jobs(request.user)
        e = None
    except Exception as e:
        jobs = []
    a = {
        "is_authenticated": request.user.is_authenticated(),
        "jobs": jobs,
    }
    return HttpResponse(simplejson.dumps(a), mimetype="application/json")

@login_required
def job_detail(request, jobid):
    e = None
    for job in utils.get_all_jobs(request.user):
        if job[0] == jobid:
            break
    else:
        job = None
        e = "That job number is not running."
    c = Context({
        "job":job,
        "error_message": e,
        })
    return render(request, "chem/job_detail.html", c)

@login_required
def reset_job(request, jobid):
    """Used to restart jobs that have hit the time limit."""
    if not request.user.is_staff:
        return HttpResponse("You must be a staff user to reset a job.")

    if request.method == "POST":
        e = None
        name = Job.objects.filter(jobid=jobid).name
        njobid, e = utils.reset_output(request.user, name)
        if e is None:
            return HttpResponse("It worked. Your new job id is: %d" % njobid)
        else:
            return HttpResponse(e)

@login_required
def kill_job(request, jobid):
    if not request.user.is_staff:
        return HttpResponse("You must be a staff user to kill a job.")

    if request.method == "POST":
        e = utils.kill_job(request.user, jobid)
        if e is None:
            try:
                job = Job.objects.filter(jobid=jobid)[0]
                job.delete()
            except IndexError:
                pass
            return redirect(job_index)
        else:
            return HttpResponse(e)