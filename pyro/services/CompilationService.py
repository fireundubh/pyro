"""
CompilationService - Handles parallel compilation of Papyrus scripts.

Extracted from BuildFacade.try_compile().
Contains TimeElapsed, CompileData, and CompileDataCaprica dataclasses.
"""
import concurrent.futures
import ctypes
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Context, Decimal, ROUND_DOWN
from typing import TYPE_CHECKING, Union

from pyro.Comparators import endswith
from pyro.Enums.ProcessState import ProcessState
from pyro.ProcessManager import ProcessManager

if TYPE_CHECKING:
    from pyro.PapyrusProject import PapyrusProject


class TimeElapsed:
    """Tracks elapsed time for compilation operations."""

    start_time: float = 0.0
    end_time: float = 0.0

    def __init__(self) -> None:
        self._context = Context(prec=4, rounding=ROUND_DOWN)
        self.start_time = 0.0
        self.end_time = 0.0

    def average(self, dividend: int) -> Decimal:
        """Calculate average time per operation."""
        if dividend == 0:
            return round(Decimal(0), 8)
        value = self.value()
        if value.compare(0) == 0:
            return round(Decimal(0), 8)
        return round(value / Decimal(dividend, self._context), 8)

    def value(self) -> Decimal:
        """Get total elapsed time."""
        return Decimal(self.end_time) - Decimal(self.start_time)


@dataclass
class CompileData:
    """Tracks compilation statistics for standard Papyrus compiler."""

    time: TimeElapsed = field(init=False, default_factory=TimeElapsed)
    scripts_count: int = field(init=False, default_factory=int)
    success_count: int = field(init=False, default_factory=int)
    command_count: int = field(init=False, default_factory=int)

    def __post_init__(self) -> None:
        self.time = TimeElapsed()

    @property
    def failed_count(self) -> int:
        """Number of scripts that failed to compile."""
        return self.command_count - self.success_count

    def to_string(self) -> str:
        """Format compilation statistics as a string."""
        raw_time, avg_time = ('{0:.3f}s'.format(t)
                              for t in (self.time.value(), self.time.average(self.success_count)))

        return f'Compile time: ' \
               f'{raw_time} ({avg_time}/script) - ' \
               f'{self.success_count} succeeded, ' \
               f'{self.failed_count} failed ' \
               f'({self.scripts_count} scripts)'


@dataclass
class CompileDataCaprica(CompileData):
    """Tracks compilation statistics for Caprica compiler."""

    @property
    def failed_count(self) -> int:
        """For Caprica, either all scripts compile or none do."""
        return 1 if self.success_count == 0 else 0

    def to_string(self) -> str:
        """Format compilation statistics as a string."""
        raw_time = '{0:.3f}s'.format(self.time.value())
        avg_time = '{0:.4f}s'.format(self.time.average(self.scripts_count))

        return f'Compile time: ' \
               f'{raw_time} ({avg_time}/script) - ' \
               f'({self.scripts_count} scripts)'


class CompilationService:
    """Service for compiling Papyrus scripts."""

    log: logging.Logger = logging.getLogger('pyro')

    def __init__(self, ppj: 'PapyrusProject') -> None:
        self.ppj = ppj
        self.compile_data: CompileData = CompileData()
        self.compile_data_caprica: CompileDataCaprica = CompileDataCaprica()

    @staticmethod
    def _limit_priority() -> None:
        """Lower process priority to avoid impacting system responsiveness."""
        if sys.platform == 'win32':
            BELOW_NORMAL_PRIORITY_CLASS = 0x4000
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
        else:
            os.nice(19)

    def is_using_caprica(self) -> bool:
        """Check if the project is configured to use Caprica compiler."""
        return endswith(self.ppj.get_compiler_path(), 'Caprica.exe', ignorecase=True)

    def get_compile_data(self) -> Union[CompileData, CompileDataCaprica]:
        """Get the appropriate compile data tracker based on compiler type."""
        return self.compile_data_caprica if self.is_using_caprica() else self.compile_data

    def _get_scripts_to_compile(self) -> dict[str, str]:
        """
        Get scripts that need compilation (handles incremental builds).

        Extracted from CompilerCommandBuilder.get_scripts_to_compile().

        Returns:
            Dictionary of object_name -> script_path
        """
        if self.ppj.options.no_incremental_build:
            psc_paths = self.ppj.psc_paths.copy()
        else:
            psc_paths = self.ppj.script_handler.try_exclude_unmodified_scripts()

        # Add scripts whose PEX counterparts are missing
        for object_name, script_path in self.ppj.missing_scripts.items():
            if object_name not in psc_paths:
                psc_paths[object_name] = script_path

        return psc_paths

    def _get_compiler(self):
        """Get appropriate compiler instance."""
        from pyro.compilers import create_compiler

        compiler_path = self.ppj.get_compiler_path()
        config_path = self.ppj.get_compiler_config_path()

        return create_compiler(compiler_path, config_path)

    def compile_sequential(self, commands: list[list[str]], compile_data: CompileData) -> None:
        """
        Compile scripts sequentially (one at a time).

        Args:
            commands: List of compiler command lists
            compile_data: Data tracker to update with results
        """
        for command in commands:
            self.log.debug(f'Command: {" ".join(command)}')
            if ProcessManager.run_compiler(command) == ProcessState.SUCCESS:
                compile_data.success_count += 1

    def compile_parallel(self, commands: list[list[str]], compile_data: CompileData, worker_limit: int) -> None:
        """
        Compile scripts in parallel using a thread pool.

        Args:
            commands: List of compiler command lists
            compile_data: Data tracker to update with results
            worker_limit: Maximum number of parallel workers
        """
        with ThreadPoolExecutor(max_workers=worker_limit) as executor:
            futures = [executor.submit(ProcessManager.run_compiler, command) for command in commands]
            for future in concurrent.futures.as_completed(futures):
                if future.result() == ProcessState.SUCCESS:
                    compile_data.success_count += 1

    def try_compile(self) -> None:
        """
        Build and execute compiler commands.

        This is the main entry point, matching the original BuildFacade.try_compile() API.
        """
        # Get scripts to compile
        psc_paths = self._get_scripts_to_compile()

        # Early exit if nothing to compile
        if not psc_paths:
            return

        # Get compiler and build commands
        compiler = self._get_compiler()
        context = self.ppj.create_compilation_context(psc_paths)
        result = compiler.build_commands(context)

        # Get appropriate compile data tracker
        compile_data = self.get_compile_data()
        compile_data.command_count = result.command_count

        compile_data.time.start_time = time.time()

        # Decide execution strategy based on compiler capabilities
        if not compiler.supports_parallel_execution(context) or result.command_count == 1:
            self.compile_sequential(result.commands, compile_data)
        elif result.command_count > 0:
            worker_limit = min(result.command_count, context.worker_limit)
            self.compile_parallel(result.commands, compile_data, worker_limit)

        compile_data.time.end_time = time.time()

        # Caprica success = all files compiled
        if result.is_batch and compile_data.success_count > 0:
            compile_data.scripts_count = compile_data.command_count
