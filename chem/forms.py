import re
import json

from django import forms
from django.http import HttpResponse
from django.template.loader import render_to_string
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML

from data.models import JobTemplate
from cluster.models import Credential
from utils import run_standard_jobs, convert_logs, parse_file_list, find_sets
from models import ErrorReport
from chemtools.constants import KEYWORDS


class MultiFileInput(forms.FileInput):

    def render(self, name, value, attrs={}):
        attrs['multiple'] = 'multiple'
        return super(MultiFileInput, self).render(name, None, attrs=attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            return [files.get(name)]


class MultiFileField(forms.FileField):
    widget = MultiFileInput
    default_error_messages = {
        'min_num': u"Ensure at least %(min_num)s file is uploaded (received %(num_files)s).",
        'max_num': u"Ensure at most %(max_num)s files are uploaded (received %(num_files)s).",
        'file_size': u"File: %(uploaded_file_name)s, exceeded maximum upload size."}

    def __init__(self, *args, **kwargs):
        self.min_num = kwargs.pop('min_num', 1)
        self.max_num = kwargs.pop('max_num', None)
        self.maximum_file_size = kwargs.pop('maximum_file_size', None)
        super(MultiFileField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        ret = []
        for item in data:
            ret.append(super(MultiFileField, self).to_python(item))
        return ret

    def validate(self, data):
        super(MultiFileField, self).validate(data)
        num_files = len(data)

        if len(data) and not data[0]:
            num_files = 0

        if num_files < self.min_num:
            raise forms.ValidationError(
                self.error_messages['min_num'] % {'min_num': self.min_num, 'num_files': num_files})
        elif self.max_num and num_files > self.max_num:
            raise forms.ValidationError(
                self.error_messages['max_num'] % {'max_num': self.max_num, 'num_files': num_files})

        for uploaded_file in data:
            if uploaded_file.size > self.maximum_file_size and self.maximum_file_size:
                raise forms.ValidationError(
                    self.error_messages['file_size'] % {'uploaded_file_name': uploaded_file.name})


class ErrorReportForm(forms.ModelForm):

    class Meta:
        model = ErrorReport
        fields = ("email", "urgency", "message")


class UploadForm(forms.Form):
    CHOICES = (
        ("logparse", "Log Parse"),
        ("longchain", "Long Chain Limit"),
        ("structureview", "Structure View"),
        ("gjfreset", "Gjf Reset"),
        ("percent", "Percent"),
    )
    files = MultiFileField()
    options = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES)
    td_reset = forms.BooleanField(required=False, label="TD Reset")
    gjf_submit = forms.BooleanField(required=False,  label="GJF Submit")
    store = forms.BooleanField(required=False,  label="Store Log File")
    split_iter = forms.BooleanField(required=False,  label="Split Log Iterations")

    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.layout = Layout(
        'files',
        'options',
        'td_reset',
        'gjf_submit',
        'store',
        'split_iter',
    )

    def clean(self):
        files = parse_file_list(self.cleaned_data.get("files"))
        if self.cleaned_data.get("options") == "longchain":
            logsets, files = find_sets(files)
            files.extend(convert_logs(logsets))
            if not len(files):
                msg = "There are no data files or set of logs to parse."
                raise forms.ValidationError(msg)
        self.cleaned_data["files"] = files
        return self.cleaned_data


class MoleculeForm(forms.Form):
    keywords = forms.CharField(initial=KEYWORDS, required=False)
    memory = forms.IntegerField(initial=59, required=False)
    nprocshared = forms.IntegerField(initial=16, required=False)
    charge = forms.IntegerField(initial=0, required=False)
    multiplicity = forms.IntegerField(initial=1, required=False)
    perturb = forms.FloatField(initial=0.0, required=False)
    scale = forms.IntegerField(initial=10, required=False)
    view = forms.BooleanField(initial=False, required=False)

    helper = FormHelper()
    helper.form_tag = False
    helper.layout = Layout(
        Div(
            HTML("""
            <div class="col-xs-12" >
                <div id="div_id_keywords" class="form-group control-group">
                    <label for="id_keywords" class="control-label ">Keywords</label>
                        <div class="entry input-group">
                            <input type="text" size=54 class="form-control" id="id_keywords" name="keywords[]" value="%s">
                            <span class="input-group-btn">
                                <button class="btn btn-add btn-primary" type="button">
                                    <span class="glyphicon glyphicon-plus"></span>
                                </button>
                            </span>
                        </div>
                </div>
            </div>
                """ % KEYWORDS),
            css_class="row",
        ),
        Div(
            Div('memory', css_class='col-xs-6'),
            Div('nprocshared', css_class='col-xs-6'),
        css_class='row'),
        Div(
            Div('charge', css_class='col-xs-6'),
            Div('multiplicity', css_class='col-xs-6'),
        css_class='row'),
        Div(
            Div('perturb', css_class='col-xs-6'),
            Div('scale', css_class='col-xs-6'),
        css_class='row'),
        'view',
    )

    def clean(self):
        super(MoleculeForm, self).clean()
        for field in self.fields:
            if self.cleaned_data.get(field) in [None, '']:
                self.cleaned_data[field] = self.fields[field].initial
        return self.cleaned_data

    def clean_keywords(self):
        try:
            return [x for x in self.data.getlist("keywords[]") if x]
        except AttributeError:
            # self.data is a dict because it does not have a request dict
            return

class JobForm(forms.Form):
    name = forms.CharField(max_length=400)
    email = forms.EmailField()
    allocation = forms.CharField(max_length=12)
    nodes = forms.IntegerField()
    walltime = forms.IntegerField()
    custom_template = forms.BooleanField(required=False)
    base_template = forms.ModelChoiceField(
        queryset=JobTemplate.objects.all(),
        to_field_name="template",
        required=False,
    )
    template = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'cols': 50,
                'rows': 26,
                'disabled': True
            }),
        required=False,
    )

    credential = forms.ModelChoiceField(
        queryset=Credential.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
        help_text="Only required if you are submitting a job.")

    helper = FormHelper()
    helper.form_tag = False
    helper.layout = Layout(
        Div(
            Div('name', css_class='col-xs-12'),
        css_class='row'),
        Div(
            Div('email', css_class='col-xs-6'),
            Div('allocation', css_class='col-xs-6'),
        css_class='row'),
        Div(
            Div('nodes', css_class='col-xs-6'),
            Div('walltime', css_class='col-xs-6'),
        css_class='row'),
        Div(
            Div('custom_template', css_class='col-xs-2'),
            Div('base_template', css_class='col-xs-10'),
        css_class='row'),
        'template',
        'credential',
    )

    def __init__(self,  *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)

    @classmethod
    def get_form(cls, request, molecule, initial=False):
        req = request.REQUEST
        a = dict(req)

        keys = set(JobForm.base_fields.keys())
        # Only raise form errors if there are values in the request that match
        # any of the field names for the form
        if not initial and a and set(a.keys()) & keys:
            form = JobForm(req, initial=a)
        else:
            if request.user.is_authenticated():
                email = request.user.email
            else:
                email = ""

            form = JobForm(initial={
                "name": molecule,
                "email": email,
                "allocation": "TG-CHE120081",
                "walltime": 48,
                "nodes": 1,
            })
        if request.user.is_authenticated():
            f = form.fields['credential']
            f.widget = forms.Select()
            f.queryset = Credential.objects.filter(user=request.user)
        return form

    def is_valid(self, method=None):
        if method == "POST":
            self.fields['credential'].required = True
        return super(JobForm, self).is_valid()

    def get_single_data(self, name):
        d = dict(self.cleaned_data)
        d["name"] = re.sub(r"{{\s*name\s*}}", name, d["name"])
        return d

    def clean(self):
        if not (self.cleaned_data.get("base_template") or
                self.cleaned_data.get("template")):
            raise forms.ValidationError(
                "A template or base template is required.")
        return self.cleaned_data

    def get_results(self, request, string, mol_form):
        job_settings = dict(self.cleaned_data)
        mol_settings = dict(mol_form.cleaned_data)
        if request.method == "GET":
            if request.REQUEST.get('molname'):
                job_settings['name'] = request.REQUEST.get('molname')
            job_string = JobTemplate.render(**job_settings)
            response = HttpResponse(job_string, content_type="text/plain")
            filename = '%s.job' % job_settings['name']
            add = "" if request.REQUEST.get("view") else "attachment; "
            response['Content-Disposition'] = add + 'filename=' + filename
            return response
        elif request.method == "POST":
            cred = job_settings.pop("credential")
            do_html = request.REQUEST.get("html", False)
            results = run_standard_jobs(
                cred, string, mol_settings, job_settings)
            if results["failed"]:
                failed_names = zip(*results['failed'])[0]
                results["failed_mols"] = ','.join(failed_names)
            if do_html:
                html = render_to_string("chem/multi_submit.html", results)
                temp = {"success": True, "html": html}
                return HttpResponse(json.dumps(temp),
                                    content_type="application/json")
            else:
                return HttpResponse(json.dumps(results),
                                    content_type="application/json")
