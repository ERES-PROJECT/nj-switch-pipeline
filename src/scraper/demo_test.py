"""Seven-supplier PSE&G electric demo using exactly the production collection path."""
import sys
from nj_switch.cli import main

SUPPLIERS = ["Constellation Energy", "Direct Energy", "Ambit Energy", "Think Energy",
             "NRG", "Major Energy", "Xoom Energy"]


def run():
    args = ["collect", "--utility", "PSE&G Electric", "--limit", "7"]
    for supplier in SUPPLIERS:
        args.extend(["--supplier", supplier])
    return main([*args, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(run())
