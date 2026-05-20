import argparse
import logging
import os
from pathlib import Path
from dotenv import dotenv_values
from . import SupersetCodec

STEPS = ["databases", "datasets", "charts", "dashboards"]


def _add_connection_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("resources_dir", metavar="RESOURCES_DIR", type=Path,
                   help="Pasta contendo os arquivos YAML de recursos.")
    p.add_argument("--url",      default=os.getenv("SUPERSET_URL", "http://localhost:8090"),
                   help="URL base do Superset.")
    p.add_argument("--user",     default=os.getenv("SUPERSET_ADMIN_USERNAME", "admin"),
                   help="Usuário admin do Superset.")
    p.add_argument("--password", default=os.getenv("SUPERSET_ADMIN_PASSWORD", "admin"),
                   help="Senha do usuário admin.")
    p.add_argument("--only", nargs="+", choices=STEPS, metavar="STEP",
                   help="Executa apenas os passos indicados (padrão: todos).")
    p.add_argument("--safe", action="store_true",
                   help=(
                       "Modo seguro: no export, armazena campos verbatim do Superset "
                       "(query_context_raw, position_json_raw, _raw em filtros desconhecidos) "
                       "garantindo roundtrip para qualquer viz_type ou tipo de filtro. "
                       "No apply, erros por recurso são logados como warning e pulados "
                       "em vez de abortar o pipeline."
                   ))


def main():
    parser = argparse.ArgumentParser(
        prog="superset-codec",
        description="Codec declarativo para recursos Apache Superset.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    apply_p = sub.add_parser("apply", help="Aplica recursos YAML ao Superset (idempotente).")
    _add_connection_args(apply_p)
    apply_p.add_argument("--vars", default=None,
                         help="Arquivo .env com variáveis para interpolação.")
    apply_p.add_argument("--with-env", action="store_true",
                         help="Inclui variáveis de ambiente (arquivo tem precedência).")

    export_p = sub.add_parser("export", help="Exporta recursos do Superset para YAML.")
    _add_connection_args(export_p)
    export_p.add_argument("--vars", default=None,
                          help="Arquivo .env: valores são substituídos por ${VAR} no output.")
    export_p.add_argument("--no-validate", action="store_true",
                          help=(
                              "Desabilita a validação por roundtrip (padrão: ativa). "
                              "Por padrão, cada chart exportado é aplicado com nome temporário, "
                              "testado via endpoint de dados e excluído automaticamente."
                          ))

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.debug("URL: %s | usuário: %s", args.url, args.user)

    if args.command == "apply":
        if not args.resources_dir.is_dir():
            parser.error(f"Pasta de recursos não encontrada: {args.resources_dir}")
        variables: dict[str, str] = {}
        if args.with_env:
            variables.update(os.environ)
        implicit_env = args.resources_dir / ".env"
        vars_path = Path(args.vars) if args.vars else (implicit_env if implicit_env.exists() else None)
        if args.vars and not vars_path.exists():
            parser.error(f"Arquivo de variáveis não encontrado: {vars_path}")
        if vars_path:
            file_vars = {k: v for k, v in dotenv_values(vars_path).items() if v is not None}
            variables.update(file_vars)
            logging.info("Carregadas %d variáveis de %s", len(file_vars), vars_path)
        codec = SupersetCodec(args.url, args.user, args.password,
                              resources_dir=args.resources_dir, variables=variables,
                              safe_mode=args.safe)
        codec.apply(steps=args.only)
        logging.info("Apply concluído.")

    elif args.command == "export":
        args.resources_dir.mkdir(parents=True, exist_ok=True)
        variables: dict[str, str] = {}
        implicit_env = args.resources_dir / ".env"
        vars_path = Path(args.vars) if args.vars else (implicit_env if implicit_env.exists() else None)
        if args.vars and not vars_path.exists():
            parser.error(f"Arquivo de variáveis não encontrado: {vars_path}")
        if vars_path:
            file_vars = {k: v for k, v in dotenv_values(vars_path).items() if v is not None}
            variables.update(file_vars)
            logging.info("Carregadas %d variáveis para inversão de %s", len(file_vars), vars_path)
        codec = SupersetCodec(args.url, args.user, args.password,
                              resources_dir=args.resources_dir, variables=variables,
                              safe_mode=args.safe)
        codec.export(steps=args.only, no_validate=args.no_validate)
        logging.info("Export concluído.")


if __name__ == "__main__":
    main()
