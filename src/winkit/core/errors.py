"""Hierarquia de exceções do WinKit (ARQUITETURA.md, R-25).

Toda exceção lançada pelo projeto herda de ``WinKitError``. A mensagem é técnica
(vai para o log); o texto para o usuário vem de ``winkit.i18n``.
"""

from __future__ import annotations


class WinKitError(Exception):
    """Raiz de todas as exceções do projeto."""


class RecipeError(WinKitError):
    """Receita inválida, incompatível ou inconsistente."""


class RecipeValidationError(RecipeError):
    """A receita viola uma ou mais regras de validação (PLANO.md §6.2)."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


class CatalogError(WinKitError):
    """Arquivo de catálogo em ``data/`` inválido ou ausente."""


class PathTemplateError(WinKitError):
    """Caminho não pode ser traduzido para molde ou o molde não pode ser resolvido."""


class PlanError(WinKitError):
    """O planejador não conseguiu montar um plano (ex.: dependência em ciclo)."""


class StateError(WinKitError):
    """Transição de estado inválida ou arquivo de estado corrompido."""


class VentoyConfigError(WinKitError):
    """``ventoy.json`` existente é inválido; nada foi alterado."""


class UnattendError(WinKitError):
    """Não foi possível gerar o ``autounattend.xml``."""


class PlatformError(WinKitError):
    """Falha ao interagir com o sistema operacional."""


class CommandError(PlatformError):
    """Um comando externo falhou ou excedeu o tempo limite."""

    def __init__(
        self, message: str, *, exit_code: int | None = None, timed_out: bool = False
    ) -> None:
        self.exit_code = exit_code
        self.timed_out = timed_out
        super().__init__(message)


class PowerShellError(CommandError):
    """Um script PowerShell terminou com erro."""


class RegistryError(PlatformError):
    """Falha ao ler ou escrever no registro."""


class VssError(PlatformError):
    """Falha ao criar, acessar ou apagar uma cópia de sombra."""


class PendriveError(WinKitError):
    """Pendrive Ventoy ausente, ambíguo ou inadequado."""


class UnsafeOperationError(WinKitError):
    """Operação recusada por violar uma salvaguarda de dados (R-18 a R-22)."""


class IntegrityError(WinKitError):
    """Hash de um arquivo do pendrive não confere com o manifesto (R-22)."""


class StepError(WinKitError):
    """Falha dentro de uma etapa do Agente."""

    def __init__(self, message: str, *, recoverable: bool = True) -> None:
        self.recoverable = recoverable
        super().__init__(message)
