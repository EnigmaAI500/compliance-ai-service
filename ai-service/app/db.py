import os
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


def _get_conn():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "InternalControlDb"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "admin"),
        cursor_factory=RealDictCursor,
    )
    return conn


def get_customer_by_no(customer_no: str) -> Optional[Dict[str, Any]]:
    sql = """
    SELECT
        "CustomerNo",
        "DocumentName",
        "MainAccount",
        "District",
        "Region",
        "Locality",
        "Street",
        "Pinfl",
        "ExpiryDate",
        "Nationality",
        "BirthCountry",
        "PassportIssuerCode",
        "PassportIssuerPlace",
        "Citizenship",
        "RegDocType",
        "RegDocNum",
        "RegDocSerialNum",
        "RegPinfl",
        "Lang",
        "CitizenshipDesc",
        "NationalityDesc",
        "AddressCode",
        "ResidentStatus",
        "RiskFlag",
        "RiskScore",
        "RiskReason"
    FROM public."Customers"
    WHERE "CustomerNo" = %s
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (customer_no,))
            row = cur.fetchone()
            return dict(row) if row else None


def update_customer_risk(
    customer_no: str,
    risk_flag: str,
    risk_score: int,
    risk_reason: str,
) -> None:
    sql = """
    UPDATE public."Customers"
    SET
        "RiskFlag"   = %s,
        "RiskScore"  = %s,
        "RiskReason" = %s
    WHERE "CustomerNo" = %s
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (risk_flag, risk_score, risk_reason, customer_no))
        conn.commit()
