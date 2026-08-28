import os
import subprocess


BRANCH_AUDIENCES = {
    "main": "music-weekly",
    "test": "test",
}


def get_edition_id(edition_date, branch: str | None = None) -> str:
    """Return a branch-scoped, deterministic production or test edition ID."""
    branch = branch or get_runtime_branch()
    date_id = edition_date.isoformat()

    if branch == "main":
        return date_id

    if branch == "test":
        run_id = os.getenv("GITHUB_RUN_ID")
        run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
        if not run_id:
            raise RuntimeError(
                "Execuções de teste precisam de GITHUB_RUN_ID para identificar "
                "unicamente cada envio. Execute o workflow Testar Music Weekly pelo GitHub Actions."
            )
        return f"test-{date_id}-run-{run_id}-attempt-{run_attempt}"

    raise RuntimeError(
        f"Branch não autorizada para envio: {branch}. "
        "Somente main e test podem enviar newsletters."
    )


def get_runtime_branch() -> str:
    """Return the branch running the application, failing closed if unknown."""
    github_branch = os.getenv("GITHUB_REF_NAME")
    if github_branch:
        return github_branch

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise RuntimeError(
            "Não foi possível determinar a branch em execução. "
            "Use main ou test."
        )

    if branch:
        return branch

    raise RuntimeError("Não foi possível determinar a branch em execução.")


def get_audience_tag(branch: str | None = None) -> str:
    """Map an allowed branch to its Kit audience tag."""
    branch = branch or get_runtime_branch()
    try:
        return BRANCH_AUDIENCES[branch]
    except KeyError as error:
        raise RuntimeError(
            f"Branch não autorizada para envio: {branch}. "
            "Somente main e test podem enviar newsletters."
        ) from error
