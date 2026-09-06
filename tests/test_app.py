import importlib
import logging
import threading
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from shared.security import validate_urls, contained_file
from shared.downloader.manager import DownloadManager
from shared.downloader.jobs import JobStatus

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MAMBAFLOW_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('MAMBAFLOW_DOWNLOAD_DIR', str(tmp_path / 'downloads'))
    import shared
    importlib.reload(shared)
    import apps.webui.main as web
    with TestClient(web.app) as client:
        yield client
    shared.get_manager().stop_event.set()

@pytest.mark.parametrize('url', ['file:///etc/passwd','http://127.0.0.1','https://youtube.com.evil.test/watch','https://user@youtube.com/watch','https://youtube.com:8443/watch','ftp://youtu.be/x'])
def test_reject_urls(url):
    with pytest.raises(ValueError): validate_urls([url])

def test_urls():
    assert validate_urls(['https://youtu.be/abc','https://youtu.be/abc']) == ['https://youtu.be/abc']
    with pytest.raises(ValueError): validate_urls([])

def test_traversal_and_symlink(tmp_path):
    root=tmp_path/'media';root.mkdir()
    outside=tmp_path/'media-secret';outside.write_text('private')
    (root/'link').symlink_to(outside)
    for relative in ('../media-secret','link',str(outside)):
        with pytest.raises(ValueError): contained_file(root,relative)

def test_ui_and_boundaries(client):
    assert 'Encuentra ese tema' in client.get('/').text
    assert client.get('/health').json()['app']=='MambaFlow'
    assert client.get('/',headers={'host':'evil.test'}).status_code==400
    assert client.post('/jobs',data={'urls':'https://youtu.be/abc'},headers={'origin':'https://evil.test'}).status_code==403
    assert client.post('/jobs',data={'urls':'file:///tmp/a'}).status_code==422
    assert client.post('/jobs',data={'urls':'https://youtu.be/abc','mode':'bad'}).status_code==422
    assert client.get('/search?q='+'x'*201).status_code==422
    for page in ('/videos','/history','/jobs'):
        assert client.get(page).status_code==200

def test_search_escapes_and_errors(client, monkeypatch):
    import apps.webui.main as web
    monkeypatch.setattr(web,'search_youtube',lambda q:[{'title':'<script>alert(1)</script>','url':'https://youtu.be/abc','uploader':'test','duration':10,'thumb':None}])
    result=client.get('/search?q=test')
    assert '&lt;script&gt;' in result.text
    monkeypatch.setattr(web,'search_youtube',lambda q: (_ for _ in ()).throw(RuntimeError()))
    assert 'No se pudo consultar' in client.get('/search?q=test').text

def test_history_concurrent(tmp_path):
    manager=DownloadManager({'history_path':str(tmp_path/'history.json')},logging.getLogger('test'))
    jobs=[manager.add_job(['https://youtu.be/test'],'audio') for _ in range(20)]
    with ThreadPoolExecutor(4) as pool: list(pool.map(manager._persist_history_entry,jobs))
    assert len(json.loads(manager.history_path.read_text()))==20
    assert manager.cancel(jobs[0].id)
    assert jobs[0].status == JobStatus.canceled

def test_media_routes_reject_sibling(client, tmp_path, monkeypatch):
    root=tmp_path/'downloads';root.mkdir(exist_ok=True)
    outside=tmp_path/'downloads-secret.mp3';outside.write_bytes(b'private')
    for endpoint in ['/play?rel=../downloads-secret.mp3','/media/../downloads-secret.mp3']:
        assert client.get(endpoint).status_code==404
    assert client.post('/reveal',data={'rel':str(outside)}).status_code==404
    assert client.post('/open_folder',data={'rel':str(outside)}).status_code==404
    assert client.get('/library').status_code==200

def test_download_final_paths_and_no_overwrite(tmp_path, monkeypatch):
    from shared.downloader.ytdlp_wrapper import Downloader
    from shared.downloader.jobs import Job, JobMode
    import yt_dlp
    final=tmp_path/'done.mp3';final.write_bytes(b'audio')
    downloader=Downloader({'download_root':str(tmp_path)},logging.getLogger('test'))
    captured={}
    class FakeDL:
        def __init__(self,options):captured.update(options)
        def extract_info(self,url,download):
            captured['progress_hooks'][0]({'filename':str(tmp_path/'gone.webm'),'status':'finished'})
            return {'requested_downloads':[{'filepath':str(final)}]}
    monkeypatch.setattr(yt_dlp,'YoutubeDL',FakeDL)
    result=downloader.download(Job(urls=['https://youtu.be/test'],mode=JobMode.audio),lambda event:None,threading.Event())
    assert result==[str(final)]
    assert captured['overwrites'] is False
    assert captured['noplaylist'] is True

def test_search_cache(monkeypatch):
    import shared.search as search
    search._cache.clear();calls=[]
    class FakeDL:
        def __init__(self,options):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):calls.append(1);return {'entries':[{'id':'abc','title':'song'}]}
    monkeypatch.setattr(search.yt_dlp,'YoutubeDL',FakeDL)
    assert search.search_youtube('song')==search.search_youtube('song')
    assert len(calls)==1
