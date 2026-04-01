import csv
import io
from datetime import datetime, date


class CSVParseError(Exception):
    pass


BANK_FORMATS = {
    "monzo": {
        "date_col": "date",
        "description_col": "name",
        "amount_col": "amount",
        "date_format": "%d/%m/%Y",
        "type_detection": "sign",
    },
    "starling": {
        "date_col": "date",
        "description_col": "counter party",
        "amount_col": "amount (gbp)",
        "date_format": "%d/%m/%Y",
        "type_detection": "sign",
    },
    "barclays": {
        "date_col": "date",
        "description_col": "memo",
        "amount_col": "amount",
        "date_format": "%d/%m/%Y",
        "type_detection": "sign",
    },
    "hsbc": {
        "date_col": "date",
        "description_col": "description",
        "paid_out_col": "paid out",
        "paid_in_col": "paid in",
        "date_format": "%d/%m/%Y",
        "type_detection": "split_columns",
    },
    "lloyds": {
        "date_col": "transaction date",
        "description_col": "transaction description",
        "debit_col": "debit amount",
        "credit_col": "credit amount",
        "date_format": "%d/%m/%Y",
        "type_detection": "split_columns",
    },
    "nationwide": {
        "date_col": "date",
        "description_col": "description",
        "paid_out_col": "paid out",
        "paid_in_col": "paid in",
        "date_format": "%d %b %Y",
        "type_detection": "split_columns",
    },
}


def detect_bank_format(headers):
    headers_lower = [h.strip().lower() for h in headers]

    if "emoji" in headers_lower and "name" in headers_lower:
        return "monzo"

    if "counter party" in headers_lower:
        return "starling"

    if "memo" in headers_lower and "subcategory" in headers_lower:
        return "barclays"

    if "transaction description" in headers_lower and "debit amount" in headers_lower:
        return "lloyds"

    if "paid out" in headers_lower and "paid in" in headers_lower:
        if "balance" in headers_lower:
            for h in headers_lower:
                if "nationwide" in h or "flexdirect" in h:
                    return "nationwide"
            return "hsbc"

    return None


def parse_date(date_string, date_format):
    date_string = date_string.strip()

    formats_to_try = [date_format, "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue

    raise CSVParseError(f"Cannot parse date: '{date_string}'")


def parse_amount(value):
    if not value or not value.strip():
        return None

    cleaned = value.strip().replace("£", "").replace(",", "").replace(" ", "")

    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def extract_transactions_from_csv(file_content):
    try:
        content = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = file_content.decode("latin-1")
        except UnicodeDecodeError:
            raise CSVParseError("Unable to read file. Please ensure it is a valid CSV file.")

    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise CSVParseError("CSV file appears to be empty or has no headers.")

    headers = reader.fieldnames
    bank_format = detect_bank_format(headers)

    if bank_format and bank_format in BANK_FORMATS:
        config = BANK_FORMATS[bank_format]
        return _parse_with_config(reader, config, bank_format)
    else:
        return _parse_generic(reader, headers)


def _parse_with_config(reader, config, bank_name):
    transactions = []
    errors = []
    row_number = 1

    for row in reader:
        row_number += 1
        row_lower = {k.strip().lower(): v for k, v in row.items() if k}

        try:
            date_val = parse_date(
                row_lower.get(config["date_col"], ""),
                config["date_format"]
            )
        except CSVParseError:
            errors.append(f"Row {row_number}: Invalid date")
            continue

        description = row_lower.get(config["description_col"], "").strip()
        if not description:
            errors.append(f"Row {row_number}: Missing description")
            continue

        if config["type_detection"] == "sign":
            amount = parse_amount(row_lower.get(config["amount_col"], ""))
            if amount is None:
                errors.append(f"Row {row_number}: Invalid amount")
                continue

            if amount < 0:
                transaction_type = "expense"
                amount = abs(amount)
            else:
                transaction_type = "income"

        elif config["type_detection"] == "split_columns":
            paid_out_key = config.get("paid_out_col") or config.get("debit_col")
            paid_in_key = config.get("paid_in_col") or config.get("credit_col")

            paid_out = parse_amount(row_lower.get(paid_out_key, ""))
            paid_in = parse_amount(row_lower.get(paid_in_key, ""))

            if paid_out and paid_out > 0:
                amount = paid_out
                transaction_type = "expense"
            elif paid_in and paid_in > 0:
                amount = paid_in
                transaction_type = "income"
            else:
                errors.append(f"Row {row_number}: No amount found")
                continue

        if amount <= 0:
            errors.append(f"Row {row_number}: Zero or negative amount after processing")
            continue

        transaction = {
            "date": date_val,
            "description": description,
            "amount": amount,
            "type": transaction_type,
            "merchant": description.split(" - ")[0].strip() if " - " in description else description.strip(),
        }

        transactions.append(transaction)

    return {
        "bank_detected": bank_name,
        "transactions": transactions,
        "total_parsed": len(transactions),
        "errors": errors,
        "error_count": len(errors)
    }


def _parse_generic(reader, headers):
    transactions = []
    errors = []
    row_number = 1

    headers_lower = [h.strip().lower() for h in headers if h]

    date_col = None
    desc_col = None
    amount_col = None
    debit_col = None
    credit_col = None

    for h in headers_lower:
        if not date_col and "date" in h:
            date_col = h
        if not desc_col and any(word in h for word in ["description", "memo", "name", "narrative", "details", "reference"]):
            desc_col = h
        if not amount_col and h in ("amount", "value", "sum"):
            amount_col = h
        if not debit_col and any(word in h for word in ["debit", "paid out", "withdrawal", "out"]):
            debit_col = h
        if not credit_col and any(word in h for word in ["credit", "paid in", "deposit", "in"]):
            credit_col = h

    if not date_col:
        raise CSVParseError("Could not identify a date column. Please check your CSV format.")

    if not desc_col:
        raise CSVParseError("Could not identify a description column. Please check your CSV format.")

    if not amount_col and not debit_col:
        raise CSVParseError("Could not identify an amount column. Please check your CSV format.")

    for row in reader:
        row_number += 1
        row_lower = {k.strip().lower(): v for k, v in row.items() if k}

        try:
            date_val = parse_date(row_lower.get(date_col, ""), "%d/%m/%Y")
        except CSVParseError:
            errors.append(f"Row {row_number}: Invalid date")
            continue

        description = row_lower.get(desc_col, "").strip()
        if not description:
            continue

        if amount_col:
            amount = parse_amount(row_lower.get(amount_col, ""))
            if amount is None:
                errors.append(f"Row {row_number}: Invalid amount")
                continue
            if amount < 0:
                transaction_type = "expense"
                amount = abs(amount)
            else:
                transaction_type = "income"
        else:
            debit = parse_amount(row_lower.get(debit_col, ""))
            credit = parse_amount(row_lower.get(credit_col, ""))
            if debit and debit > 0:
                amount = debit
                transaction_type = "expense"
            elif credit and credit > 0:
                amount = credit
                transaction_type = "income"
            else:
                continue

        if amount <= 0:
            continue

        transaction = {
            "date": date_val,
            "description": description,
            "amount": amount,
            "type": transaction_type,
            "merchant": description.split(" - ")[0].strip() if " - " in description else description.strip(),
        }

        transactions.append(transaction)

    return {
        "bank_detected": "unknown",
        "transactions": transactions,
        "total_parsed": len(transactions),
        "errors": errors,
        "error_count": len(errors)
    }