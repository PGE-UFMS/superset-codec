import argparse
import logging
import os
from pathlib import Path
from dotenv import dotenv_values
from . import SupersetProvisioner

def main():
    parser = argparse.ArgumentParser(
        description="Provisiona recursos do Superset a partir de arquivos JSON."
    )
    parser.add_argument(
        "resources_dir",
        metavar="RESOURCES_DIR",
        type=Path,
        help="Caminho da pasta contendo os arquivos JSON de recursos.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=["databases", "datasets", "charts", "dashboards"],
        metavar="STEP",
        help="Executa apenas os passos indicados (padrão: todos).",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SUPERSET_URL", "http://localhost:8090"),
        help="URL base do Superset.",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("SUPERSET_ADMIN_USERNAME", "admin"),
        help="Usuário admin do Superset.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SUPERSET_ADMIN_PASSWORD", "admin"),
        help="Senha do usuário admin.",
    )
    parser.add_argument(
        "--vars",
        default=None,
        help="Arquivo de variáveis para interpolação",
    )
    parser.add_argument(
        "--with-env",
        action="store_true",
        help="Mescla as variáveis do ambiente com as variáveis do arquivo (arquivo tem precedência).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.debug("URL: %s | usuário: %s", args.url, args.user)

    if not args.resources_dir.is_dir():
        parser.error(f"Pasta de recursos não encontrada: {args.resources_dir}")

    variables: dict[str, str] = {}
    if args.with_env:
        variables.update(os.environ)
    if args.vars:
        vp = Path(args.vars)
        if not vp.exists():
            parser.error(f"Arquivo de variáveis não encontrado: {vp}")
        else:
            file_vars = {k: v for k, v in dotenv_values(vp).items() if v is not None}
            variables.update(file_vars)
            logging.info("Carregadas %d variáveis de %s", len(file_vars), vp)

    provisioner = SupersetProvisioner(
        args.url,
        args.user,
        args.password,
        resources_dir=args.resources_dir,
        variables=variables,
    )
    provisioner.sync_all(steps=args.only)
    logging.info("Provisionamento concluído.")


if __name__ == "__main__":
    main()
