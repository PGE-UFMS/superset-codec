import argparse, os, sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from . import SupersetProvisioner

def main():
    parser = argparse.ArgumentParser(
        description="Provisiona recursos do Superset a partir de arquivos JSON."
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
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.debug("URL: %s | usuário: %s", args.url, args.user)

    ep = Path(__file__) / ".env"
    if ep.exists():
        load_dotenv(ep, override=False)
        logging.info("Loaded .env")


    provisioner = SupersetProvisioner(args.url, args.user, args.password, variables=os.environ)
    try:
        provisioner.sync_all(steps=args.only)
        logging.info("Provisionamento concluído.")
    except Exception as exc:
        logging.error("Provisionamento falhou: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
