from recap.core.models import RunReport


class ReleaseExecutor:
    def execute(self, report: RunReport) -> str:
        del report
        return "not_configured"
