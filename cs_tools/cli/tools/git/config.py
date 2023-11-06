from typing import List, Dict, Union

import typer
from httpx import HTTPStatusError
from rich.align import Align
from rich.table import Table

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.types import GUID

Identifier = Union[GUID, int, str]

app = CSToolsApp(
    name="config",
    help="Tools for working with git configurations.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.command(dependencies=[thoughtspot], name="create")
def config_create(
        ctx: typer.Context,
        repository_url: str = typer.Option(..., help="the git repository to use"),
        username: str = typer.Option(..., help="the username to use for the git repository"),
        access_token: str = typer.Option(..., help="the access token to use for the git repository"),
        org: str = typer.Option(None, help="the org to use if any"),
        branch_names: str = typer.Option(None,
                                         custom_type=MultipleChoiceType(),
                                         help="the branch names to use for the git repository"),
        commit_branch_name: str = typer.Option(None, help="the default branch name to use for the git repository"),
        enable_guid_mapping: bool = typer.Option(False, help="the enable guid mapping to use for the git repository"),
        configuration_branch_name: str = typer.Option(None,
                                                      help="the branch name to use for configuration and GUID mappings."),
):
    """
    Creates a configuration for a cluster or org. An org can only have a single configuration.
    """
    ts = ctx.obj.thoughtspot

    # check for required parameters
    if repository_url is None or username is None or access_token is None:
        rich_console.print("[b red]Must minimally provide the repository, username, and access_token.")
        return

    if org is not None:
        ts.org.switch(org)

    try:
        r = ts.api_v2.vcs_git_config_create(
            repository_url=repository_url,
            username=username,
            access_token=access_token,
            org_identifier=org,
            branch_names=branch_names,
            commit_branch_name=commit_branch_name,
            enable_guid_mapping=enable_guid_mapping,
            configuration_branch_name=configuration_branch_name,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error creating the configuration: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    _show_configs_as_table([r.json()], title="New Configuration Details")

@app.command(dependencies=[thoughtspot], name="update")
def config_update(
        ctx: typer.Context,
        username: str = typer.Option(None, help="the username to use for the git repository"),
        access_token: str = typer.Option(None, help="the access token to use for the git repository"),
        org: str = typer.Option(None, help="the org to update the configuration for"),
        branch_names: str = typer.Option(None,
                                         custom_type=MultipleChoiceType(),
                                         help="the branch names to use for the git repository"),
        commit_branch_name: str = typer.Option(None, help="the default branch name to use for commits"),
        enable_guid_mapping: bool = typer.Option(False, help="the enable guid mapping to use for the git repository"),
        configuration_branch_name: str = typer.Option(None,
                                                      help="the branch name to use for configuration and GUID mappings."),
):
    """
    Updates a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    try:
        r = ts.api_v2.vcs_git_config_update(
            username=username,
            access_token=access_token,
            org_identifier=org,
            branch_names=branch_names,
            commit_branch_name=commit_branch_name,
            enable_guid_mapping=enable_guid_mapping,
            configuration_branch_name=configuration_branch_name,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error creating the configuration: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    _show_configs_as_table([r.json()], title="Updated Configuration Details")


@app.command(dependencies=[thoughtspot], name="search")
def config_search(
        ctx: typer.Context,
        org: str = typer.Option(None, help="the org run in"),
        org_ids: str = typer.Option(None, custom_type=MultipleChoiceType(),
                                    help="The org IDs to get the configuration for"),
):
    """
    Searches for configurations.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    try:
        r = ts.api_v2.vcs_git_config_search(org_ids=org_ids)
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error creating the configuration: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    configs = r.json()
    _show_configs_as_table(configs)


@app.command(dependencies=[thoughtspot], name="delete")
def config_delete(
        ctx: typer.Context,
        org: str = typer.Option(None, help="the org id to delete from"),
        cluster_level: bool = typer.Option(False, help="the cluster level to use for the git repository"),
):
    """
    Deletes a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)
    else:
        # DEV NOTE: delete doesn't take an org, so it will use whatever the last one was.
        # It might be prudent to prompt to user if they want to continue.  It won't apply to
        # non-org enabled clusters.
        rich_console.print("[bold yellow]No org specified, the config in the current org will be deleted.")

    try:
        r = ts.api_v2.vcs_git_config_delete(cluster_level=cluster_level)
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error creating the configuration: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    rich_console.print(f"[green]Deleted the configuration: {r}.")


def _show_configs_as_table(configs: List[Dict], title: str = "Configuration Details"):
    """
    Show the configurations as a table.
    """
    use_cnt = len(configs) > 1

    for count, config in enumerate(configs, start=1):
        title = f"{title} {count}" if use_cnt else title
        table = Table(title=f"Configuration Details {count}", width=100)
        table.add_column("Property", width=25)
        table.add_column("Value", width=75)

        for k, v in config.items():
            table.add_row(k, str(v))

        rich_console.print(Align.center(table))
