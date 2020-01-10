import argparse


class PyroRawDescriptionHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog: str, indent_increment: int = 2, max_help_position: int = 35, width: int = 80) -> None:
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        """
        Remove metavars from printing (w/o extra space before comma)
        and support tuple metavars for positional arguments
        """
        _print_metavar = False

        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar = self._metavar_formatter(action, default)(1)
            return ', '.join(metavar)

        parts: list = []

        if action.nargs == 0:
            parts.extend(action.option_strings)
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = f' {self._format_args(action, default)}' if _print_metavar else ''
            for option_string in action.option_strings:
                parts.append(f'{option_string}{args_string}')

        return ', '.join(parts)

    def _get_default_metavar_for_optional(self, action: argparse.Action) -> str:
        return ''


class PyroRawTextHelpFormatter(argparse.RawTextHelpFormatter, PyroRawDescriptionHelpFormatter):
    pass
