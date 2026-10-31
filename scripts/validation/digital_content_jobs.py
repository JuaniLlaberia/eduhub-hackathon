"""
Reproduce the Cuenta Satélite de Cultura digital-content job figures used in docs/validation.md.

Usage: python scripts/validation/digital_content_jobs.py <path/to/csc27-puestos-t-reg-no-reg-indeptes-sector.csv>
Source: https://datos.cultura.gob.ar/dataset/1ba8cfc4-a1e6-4f29-bc6e-0a0347989e76
"""
import sys
import pandas as pd

def report(df: pd.DataFrame) -> None:
    """
    Print yearly digital-content jobs and their registered/unregistered/self-employed split.
    """
    for _, row in df.iterrows():
        registered = row["ptos_reg_contenido_digital"]
        unregistered = row["ptos_no_reg_contenido_digital"]
        self_employed = row["ptos_no_asal_contenido_digital"]
        total = registered + unregistered + self_employed
        print(
            f"{row['indice_tiempo'][:4]}: {int(total)} jobs | registered {100 * registered / total:.1f}% "
            f"| unregistered {100 * unregistered / total:.1f}% | self-employed {100 * self_employed / total:.1f}%"
        )

def main() -> None:
    """
    Load the CSV given as first argument and print the report.
    """
    report(pd.read_csv(sys.argv[1], encoding="utf-8-sig"))

if __name__ == "__main__":
    main()
