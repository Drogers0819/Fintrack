import io


class TestCSVUpload:

    def test_upload_monzo_csv(self, auth_client):
        csv_content = (
            "Date,Time,Type,Name,Emoji,Category,Amount,Currency,Local amount,Local currency,Notes and #tags\n"
            "25/03/2026,14:30,Card,Tesco,,Groceries,-52.40,GBP,-52.40,GBP,\n"
            "24/03/2026,09:15,Card,Uber,,Transport,-12.80,GBP,-12.80,GBP,\n"
            "01/03/2026,,Income,Salary,,,1700.00,GBP,1700.00,GBP,\n"
        )

        data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result["bank_detected"] == "monzo"
        assert result["created"] == 3

    def test_upload_lloyds_csv(self, auth_client):
        csv_content = (
            "Transaction Date,Transaction Type,Sort Code,Account Number,Transaction Description,Debit Amount,Credit Amount,Balance\n"
            "25/03/2026,DEB,,12345678,TESCO STORES,52.40,,1200.00\n"
            "01/03/2026,FPO,,12345678,SALARY,,1700.00,2900.00\n"
        )

        data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result["bank_detected"] == "lloyds"
        assert result["created"] == 2

    def test_upload_hsbc_csv(self, auth_client):
        csv_content = (
            "Date,Type,Description,Paid out,Paid in,Balance\n"
            "25/03/2026,POS,TESCO STORES,52.40,,1200.00\n"
            "01/03/2026,CR,SALARY,,1700.00,2900.00\n"
        )

        data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result["bank_detected"] == "hsbc"
        assert result["created"] == 2

    def test_upload_duplicate_prevention(self, auth_client):
        csv_content = (
            "Date,Time,Type,Name,Emoji,Category,Amount,Currency,Local amount,Local currency,Notes and #tags\n"
            "25/03/2026,14:30,Card,Tesco,,Groceries,-52.40,GBP,-52.40,GBP,\n"
        )

        data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        auth_client.post("/api/upload/csv", data=data, content_type="multipart/form-data")

        data2 = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data2,
            content_type="multipart/form-data"
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result["created"] == 0
        assert result["skipped"] == 1

    def test_upload_no_file(self, auth_client):
        response = auth_client.post(
            "/api/upload/csv",
            content_type="multipart/form-data"
        )
        assert response.status_code == 400

    def test_upload_wrong_extension(self, auth_client):
        data = {"file": (io.BytesIO(b"not a csv"), "statement.txt")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )
        assert response.status_code == 400

    def test_upload_empty_file(self, auth_client):
        data = {"file": (io.BytesIO(b""), "statement.csv")}
        response = auth_client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )
        assert response.status_code == 400

    def test_upload_without_auth(self, client):
        csv_content = "Date,Amount,Description\n25/03/2026,50.00,Test\n"
        data = {"file": (io.BytesIO(csv_content.encode("utf-8")), "statement.csv")}
        response = client.post(
            "/api/upload/csv",
            data=data,
            content_type="multipart/form-data"
        )
        assert response.status_code == 401
