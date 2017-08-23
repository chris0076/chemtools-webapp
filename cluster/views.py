import logging
import json

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from account.utils import add_account_page, PAGES
from models import CredentialForm, ClusterForm, Cluster, Credential
import interface
from utils import get_credentials_from_request, get_clusters_from_request


logger = logging.getLogger(__name__)


@login_required
def job_index(request):
    return render(request, "cluster/job_index.html")


@login_required
def cluster_job_index(request, cluster):
    c = {
        "cluster": cluster,
    }
    return render(request, "cluster/job_index.html", c)


@login_required
def get_job_list(request):
    cluster = request.REQUEST.get("cluster", "")
    if cluster:
        creds = request.user.credentials.filter(cluster__name__iexact=cluster)
    else:
        creds = request.user.credentials.all()

    jobs = interface.get_all_jobs(creds)
    a = {
        "is_authenticated": request.user.is_authenticated(),
        "clusters": jobs,
    }
    if request.REQUEST.get("html", ''):
        return render(request, "cluster/job_table.html", a)
    return HttpResponse(json.dumps(a), content_type="application/json")


@login_required
def job_detail(request, cluster, jobid):
    credential = Credential.objects.get(
        user=request.user, cluster__name=cluster)
    results = interface.get_specific_jobs(credential, [jobid])
    if results["error"]:
        e = results["error"]
        job = None
    elif results["failed"]:
        e = results["failed"][0][1]
        job = None
    else:
        job = results["worked"][0][1]
        e = None
    c = {
        "job": job,
        "cluster": cluster,
        "error_message": e,
    }
    return render(request, "cluster/job_detail.html", c)


@login_required
def kill_job(request, cluster):
    if request.method != "POST":
        return redirect(job_index)

    jobids = []
    for key in request.POST:
        try:
            int(key)
            jobids.append(key)
        except ValueError:
            logger.warn("Invalid key '%s' for cluser '%s'" % (key, cluster))
            pass
    credential = Credential.objects.get(
        user=request.user, cluster__name=cluster)
    result = interface.kill_jobs(credential, jobids)
    if result["error"] is None:
        return redirect(job_index)
    else:
        return HttpResponse(result["error"])


@login_required
@add_account_page("credentials")
def credential_settings(request, username):
    state = "Change Settings"
    initial = {"username": request.user.xsede_username}
    working_creds = []
    failing_creds = []
    if request.method == "POST":
        if "delete" in request.POST:
            form = CredentialForm(request.user, initial=initial)
            i = 0
            for i, cred in enumerate(get_credentials_from_request(request)):
                cred.delete()
            logger.info("%s deleted %d credential(s)" % (username, i+1))
            state = "Settings Successfully Saved"

        elif "test" in request.POST:
            form = CredentialForm(request.user, initial=initial)
            for cred in get_credentials_from_request(request):
                if cred.connection_works():
                    working_creds.append(cred)
                else:
                    failing_creds.append(cred)

        else:
            form = CredentialForm(request.user, request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.save()
                logger.info("%s updated their credentials" % username)
                state = "Settings Successfully Saved"
                form = CredentialForm(request.user, initial=initial)
    else:
        form = CredentialForm(request.user, initial=initial)

    c = {
        "pages": PAGES,
        "page": "credentials",
        "state": state,
        "form": form,
        "failing_creds": failing_creds,
        "working_creds": working_creds,
    }
    return render(request, "cluster/credential_settings.html", c)


@login_required
@add_account_page("clusters")
def cluster_settings(request, username):
    state = "Change Settings"

    if request.method == "POST":
        form = ClusterForm(request.user, request.POST)
        if "delete" in request.POST:
            i = 0
            for i, cluster in enumerate(get_clusters_from_request(request)):
                cluster.delete()
            logger.info("%s deleted %d clusters(s)" % (username, i+1))
            state = "Settings Successfully Saved"
            form = ClusterForm(request.user)

        elif "save" in request.POST:
            if form.is_valid():
                obj = form.save(commit=False)
                obj.creator = request.user
                obj.save()
                state = "Settings Successfully Saved"
                form = ClusterForm(request.user)

    else:
        form = ClusterForm(request.user)

    c = {
        "pages": PAGES,
        "page": "clusters",
        "state": state,
        "form": form,
        "clusters": Cluster.get_clusters(request.user),
    }
    return render(request, "cluster/cluster_settings.html", c)


