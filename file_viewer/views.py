import os
from mimetypes import guess_type

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http.response import FileResponse
from django.shortcuts import render
from pygments import highlight as pyghi
from pygments.formatters import html as pygform
import pygments.lexers

import file_viewer.permissions as p
import common.models as m


@login_required()
def download_file(request, sub_id, filename):
    """This is the main public entry point for getting and
    reading a file from the web browser. It looks for the given
    @sub_id and @filename. assume version 'none' to get latest"""
    return download_versioned_file(request, sub_id, None, filename)


@login_required()
def download_versioned_file(request, sub_id, version, filename):
    """This is the main entry point for when a specific
    @version number of @filename in @sub_id is requested"""
    submisison = m.Submission.objects.get(id=sub_id)
    file = os.path.join(submisison.originals_path(version), filename)
    context_tag = request.GET["context"] if "context" in request.GET else None
    version_tag = int(version) if version is not None else None
    context = (context_tag, version_tag) if context_tag is not None else None
    if not p.can_view_submission(request.user, submisison, context):
        return HttpResponseForbidden("You are not allowed to see this file")
    if 'show' in request.GET:
        return render_file(request, file, filename)
    return attachment_file(file, filename)


def render_file(request, file, filename):
    """For a given @file path and @filename, pretty print the contents
    of the file as an HTML page using pygments"""
    mime = guess_type(filename, True)
    if mime[0] is None or mime[0].split('/')[0] != 'text':
        response = FileResponse(open(file, "rb"))
        response['Content-Type'] = str(guess_type(filename, False)[0])
        return response
    with open(file, mode="r", encoding="utf-8", errors='ignore') as open_file:
        content = open_file.read()
    lexermime = 'text/x-java' if mime[0] == 'text/x-java-source' else mime[0]
    lexer = pygments.lexers.get_lexer_for_mimetype(lexermime)
    detail = {
        "content": pyghi(content, lexer, pygform.HtmlFormatter(encoding='utf-8',linenos='table')),
        "filename": filename
    }
    return render(request, 'file_viewer/pretty_file.html', detail)


def attachment_file(file, filename):
    """return a @file fieldfile and @filename
     as an http attachment"""
    response = FileResponse(open(file, "rb"))
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    response['Content-Length'] = os.stat(file).st_size
    return response
