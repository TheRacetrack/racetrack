from pathlib import Path
from typing import List

from django.shortcuts import render
from django.http import HttpResponse
import markdown

from racetrack_commons.entities.dto import PluginConfigDto
from racetrack_commons.entities.info_client import LifecycleInfoClient


def view_docs_index(request):
    docs_path = _get_docs_root_dir()
    docs = []
    for doc_file in sorted(docs_path.rglob('*.md')):
        doc_path_str = doc_file.relative_to(docs_path)
        docs.append({
            'url': f'/dashboard/docs/file/{doc_path_str.as_posix()}',
            'title': _humanize_path_title(doc_path_str),
        })

    info_client = LifecycleInfoClient()
    plugins_info: List[PluginConfigDto] = info_client.get_plugins_info()
    for plugin_info in plugins_info:
        markdown_content = info_client.get_plugin_docs(plugin_info.name)
        if markdown_content:
            docs.append({
                'url': f'/dashboard/docs/plugin/{plugin_info.name}',
                'title': f'Plugin: {plugin_info.name}',
            })

    context = {
        'docs': docs,
    }
    return render(request, 'racetrack/doc_index.html', context)


def view_doc_page(request, doc_path: str):
    docs_path = _get_docs_root_dir()
    doc_file_path = docs_path / doc_path
    if not doc_file_path.absolute().as_posix().startswith(docs_path.as_posix()):
        return HttpResponse('file path escaped allowed directory', status=400)
    if doc_file_path.suffix != '.md':
        return HttpResponse('only markdown files are allowed to fetch', status=400)

    markdown_content = doc_file_path.read_text()
    html = _generate_html_docs(markdown_content)

    context = {
        'doc_name': doc_path,
        'html_content': html,
    }
    return render(request, 'racetrack/doc_page.html', context)


def view_doc_plugin(request, plugin_name: str):
    info_client = LifecycleInfoClient()
    markdown_content = info_client.get_plugin_docs(plugin_name)
    if markdown_content is None:
        return HttpResponse('plugin docs not found', status=500)

    html = _generate_html_docs(markdown_content)

    context = {
        'doc_name': f'Plugin: {plugin_name}',
        'html_content': html,
    }
    return render(request, 'racetrack/doc_page.html', context)


def _get_docs_root_dir() -> Path:
    docs_path = Path('.').absolute().parent / 'docs'
    assert docs_path.is_dir()
    return docs_path


def _generate_html_docs(markdown_content: str) -> str:
    # missing blank lines before enumeration
    markdown_content = markdown_content.replace(':\n- ', ':\n\n- ')
    return markdown.markdown(markdown_content, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.sane_lists',
    ])


def _humanize_path_title(path: Path) -> str:
    title = ' / '.join([p.name for p in path.parents]) + path.stem
    title = title.replace('-', ' ').replace('_', ' ')
    return title.title()
