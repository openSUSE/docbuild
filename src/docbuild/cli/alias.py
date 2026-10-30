"""Small Click group supporting aliases for docbuild subcommands."""

from collections.abc import Callable, Sequence
from typing import Any

import click


class AliasGroup(click.Group):
    """Register aliases while keeping canonical command names authoritative."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self._aliases: dict[str, str] = {}

    def add_command(
        self,
        cmd: click.Command,
        name: str | None = None,
        aliases: str | Sequence[str] = (),
    ) -> None:
        """Register a command with one alias or a sequence of aliases."""
        super().add_command(cmd, name)
        target = name or cmd.name
        assert target is not None  # Click rejects unnamed commands above.
        if isinstance(aliases, str):
            aliases = (aliases,)
        for alias in aliases:
            self._aliases[alias] = target

    def command(
        self,
        *args: Any,  # noqa: ANN401
        aliases: str | Sequence[str] = (),
        **kwargs: Any,  # noqa: ANN401
    ) -> Callable[[Callable[..., Any]], click.Command]:
        """Decorate a subcommand, optionally registering alternative names."""
        register = super().command(*args, **kwargs)

        def decorator(callback: Callable[..., Any]) -> click.Command:
            cmd = register(callback)
            self.add_command(cmd, aliases=aliases)
            return cmd

        return decorator

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Look up canonical commands before resolving aliases."""
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        return super().get_command(ctx, self._aliases.get(cmd_name, cmd_name))

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Show each visible command once, with its effective aliases."""
        commands = [
            (name, cmd)
            for name in self.list_commands(ctx)
            if (cmd := self.get_command(ctx, name)) is not None and not cmd.hidden
        ]
        if not commands:
            return
        labels = []
        for name, cmd in commands:
            aliases = sorted(
                alias
                for alias, target in self._aliases.items()
                if target == name and alias not in self.commands
            )
            label = f"{name} ({', '.join(aliases)})" if aliases else name
            labels.append((label, cmd))
        limit = formatter.width - 6 - max(len(label) for label, _ in labels)
        with formatter.section("Commands"):
            formatter.write_dl(
                [(label, cmd.get_short_help_str(limit)) for label, cmd in labels]
            )
