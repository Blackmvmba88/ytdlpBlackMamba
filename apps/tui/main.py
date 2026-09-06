from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Button, Label, Static, RadioSet, ProgressBar, Footer, Header
from shared import get_manager
from shared.downloader.jobs import Job, JobStatus

class JobWidget(Static):
    def __init__(self, job: Job):
        super().__init__()
        self.job_id = job.id
        self.label = Label(f"{job.mode.value.upper()} {job.id[:8]}")
        self.progress = ProgressBar(total=100)
        self.msg = Label("")
    def compose(self):
        yield self.label
        yield self.progress
        yield self.msg

class DownloadApp(App):
    TITLE = "Descargas yt-dlp (TUI)"
    BINDINGS = [("q","quit","Salir")]
    CSS = """
    Screen { layers: base; }
    """
    def __init__(self):
        super().__init__()
        self.manager = get_manager()
        self.job_widgets = {}
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Label("Ingrese URL(s) separadas por espacios o saltos de línea:")
            self.urls = Input(placeholder="https://youtu.be/BaW_jenozKc", name="urls")
            yield self.urls
            yield Label("Modo:")
            self.mode = RadioSet()
            self.mode.add_radio_button("Video", id="video", value=True)
            self.mode.add_radio_button("Audio", id="audio")
            yield self.mode
            with Horizontal():
                yield Button("Descargar", id="btn_descargar", variant="success")
                yield Button("Cancelar último", id="btn_cancelar", variant="warning")
        yield Label("Cola y progreso:")
        self.scroll = VerticalScroll()
        yield self.scroll
        yield Footer()
    def on_mount(self):
        self.manager.start()
        self.set_interval(0.5, self.refresh_jobs)
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_descargar":
            text = (self.urls.value or "").strip()
            urls = [u for u in text.replace("\n"," ").split(" ") if u]
            mode = self.mode.pressed.id if self.mode.pressed else "video"
            if urls:
                job = self.manager.add_job(urls, mode)
                self.add_job_widget(job)
                self.urls.value = ""
        elif event.button.id == "btn_cancelar":
            jobs = self.manager.list_jobs()
            if jobs:
                self.manager.cancel(jobs[-1].id)
    def add_job_widget(self, job: Job):
        jw = JobWidget(job)
        self.job_widgets[job.id] = jw
        self.scroll.mount(jw)
    def refresh_jobs(self):
        jobs = self.manager.list_jobs()
        for job in jobs:
            if job.id not in self.job_widgets:
                self.add_job_widget(job)
            jw = self.job_widgets[job.id]
            status_label = job.status.value if hasattr(job.status, "value") else str(job.status)
            jw.label.update(f"{job.mode.value.upper()} {job.id[:8]} - {status_label} - {job.current or ''}")
            jw.progress.update(progress=job.progress)
            if job.status in (JobStatus.completed, JobStatus.error, JobStatus.canceled):
                jw.msg.update(f"{job.message or ''} {', '.join(job.output_paths) if job.output_paths else ''}")

def run():
    app = DownloadApp()
    app.run()

if __name__ == "__main__":
    run()
