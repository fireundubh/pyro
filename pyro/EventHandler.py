import logging

from pyro.Enums.Event import (Event,
                              ImportEvent,
                              BuildEvent,
                              CompileEvent,
                              AnonymizeEvent,
                              PackageEvent,
                              ZipEvent)
from pyro.ProcessManager import ProcessManager


class EventHandler:
    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, papyrus_project) -> None:
        self.project = papyrus_project
        self.xml_handler = papyrus_project.xml_handler

    def try_run_event(self, event: Event) -> None:
        if event == ImportEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_import_node, self.project.project_path)
        elif event == ImportEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_import_node, self.project.project_path)
        elif event == BuildEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_build_node, self.project.project_path)
        elif event == BuildEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_build_node, self.project.project_path)
        elif event == CompileEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_compile_node, self.project.project_path)
        elif event == CompileEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_compile_node, self.project.project_path)
        elif event == AnonymizeEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_anonymize_node, self.project.project_path)
        elif event == AnonymizeEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_anonymize_node, self.project.project_path)
        elif event == PackageEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_package_node, self.project.project_path)
        elif event == PackageEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_package_node, self.project.project_path)
        elif event == ZipEvent.PRE:
            ProcessManager.run_event(self.xml_handler.pre_zip_node, self.project.project_path)
        elif event == ZipEvent.POST:
            ProcessManager.run_event(self.xml_handler.post_zip_node, self.project.project_path)
        else:
            raise NotImplementedError
