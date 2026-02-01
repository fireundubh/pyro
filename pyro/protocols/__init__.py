"""
Protocol definitions for Pyro build system.

Protocols serve as formal interfaces documenting expected contracts
and improving type safety through static analysis.
"""

from pyro.protocols.CompilerProtocol import CompilerProtocol

__all__ = ['CompilerProtocol']
