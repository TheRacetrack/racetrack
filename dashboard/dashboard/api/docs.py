from pathlib import Path

from fastapi import FastAPI
import markdown

from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.entities.plugin_client import LifecyclePluginClient


def setup_docs_endpoints(app: FastAPI):

    @app.get('/api/docs/index')
    def _get_docs_index() -> dict:
        docs_path = _get_docs_root_dir()
        doc_pages = []
        for doc_file in sorted(docs_path.rglob('*.md')):
            doc_path_str = doc_file.relative_to(docs_path)
            doc_pages.append({
                'url': f'{doc_path_str.as_posix()}',
                'title': _humanize_path_title(doc_path_str),
            })

        plugin_pages = []
        plugin_client = LifecyclePluginClient()
        plugin_manifests: list[PluginManifest] = plugin_client.get_plugins_info()
        for plugin_manifest in plugin_manifests:
            markdown_content = plugin_client.get_plugin_docs(plugin_manifest.name)
            if markdown_content:
                plugin_pages.append({
                    'url': plugin_manifest.name,
                    'title': f'Plugin: {plugin_manifest.name}',
                })

        return {
            'doc_pages': sorted(doc_pages, key=lambda x: x['title'].lower()),
            'plugin_pages': sorted(plugin_pages, key=lambda x: x['title'].lower()),
        }
    
    @app.get('/api/docs/page/{doc_path:path}')
    def _get_docs_page(doc_path: str) -> dict:
        docs_path = _get_docs_root_dir()
        doc_file_path = docs_path / doc_path
        if not doc_file_path.absolute().as_posix().startswith(docs_path.as_posix()):
            raise RuntimeError('file path escaped allowed directory')
        if doc_file_path.suffix != '.md':
            raise RuntimeError('only markdown files are allowed to fetch')

        markdown_content = doc_file_path.read_text()
        html = _generate_html_docs(markdown_content)
        return {
            'doc_name': doc_path,
            'html_content': html,
        }
    
    @app.get('/api/docs/plugin/{plugin_name}')
    def _get_docs_plugin_page(plugin_name: str) -> dict:
        plugin_client = LifecyclePluginClient()
        markdown_content = plugin_client.get_plugin_docs(plugin_name)
        if markdown_content is None:
            raise RuntimeError('plugin docs not found')

        html = _generate_html_docs(markdown_content)
        return {
            'doc_name': f'Plugin: {plugin_name}',
            'html_content': html,
        }


def _generate_html_docs(markdown_content: str) -> str:
    # missing blank lines before enumeration
    markdown_content = markdown_content.replace(':\n- ', ':\n\n- ')
    return markdown.markdown(markdown_content, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.sane_lists',
    ])


def _get_docs_root_dir() -> Path:
    docs_path = Path('.').absolute().parent / 'docs'
    assert docs_path.is_dir()
    return docs_path


def _humanize_path_title(path: Path) -> str:
    title = ' / '.join([p.name for p in path.parents]) + path.stem
    title = title.replace('-', ' ').replace('_', ' ')
    return title.title()
