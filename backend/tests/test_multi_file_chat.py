import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ColumnDef

PK_DIR = Path("/workspace/doc/EO035/EO035药理测试原始数据/犬和猴PK数据")

PK_COLS = [
    {"field": "cpds_id", "title": "Cpds ID", "type": "text"},
    {"field": "iv_1mpk_cl_l_h_kg", "title": "IV (1 mpk) CL (L/h/kg)", "type": "number"},
    {"field": "iv_1mpk_vss_l_kg", "title": "IV (1 mpk) Vss (L/kg)", "type": "number"},
    {"field": "iv_1mpk_auc0_t_h_ng_ml", "title": "IV (1 mpk) AUC0-t (h*ng/mL)", "type": "number"},
    {"field": "iv_1mpk_t1_2_hr", "title": "IV (1 mpk) T1/2 (hr)", "type": "number"},
    {"field": "po_5_mpk_cmax_ng_ml", "title": "PO (5 mpk) Cmax (ng/mL)", "type": "number"},
    {"field": "po_5_mpk_tmax_hr", "title": "PO (5 mpk) Tmax (hr)", "type": "number"},
    {"field": "po_5_mpk_auc0_t_h_ng_ml", "title": "PO (5 mpk) AUC0-t (h*ng/mL)", "type": "number"},
    {"field": "po_5_mpk_t1_2_hr", "title": "PO (5 mpk) T1/2 (hr)", "type": "number"},
    {"field": "po_5_mpk_pct_f", "title": "PO (5 mpk) %F", "type": "number"},
]


def _upload_all(client: TestClient) -> list[tuple[str, str]]:
    out = []
    for path in sorted(PK_DIR.glob("*.xlsx")):
        with path.open("rb") as f:
            res = client.post("/api/recognize/upload", files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self_ok = res.status_code == 200
        assert self_ok, res.text
        out.append((path.name, res.json()["file_id"]))
    return out


class MultiFileChatTest(unittest.TestCase):
    def test_stream_processes_each_file_and_merges_dog_rows(self):
        client = TestClient(app)
        uploaded = _upload_all(client)
        file_ids = [fid for _, fid in uploaded]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "请识别"}],
                "columns": PK_COLS,
                "file_ids": file_ids,
                "table_name": "Dog PK",
                "auto_skill": True,
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertNotIn("504", body)
        self.assertIn("附件 1/4", body)
        self.assertIn("附件 4/4", body)
        self.assertIn("event: done", body)
        # 4 个文件一起导入 Dog PK：只应留下两只犬化合物，不应混入 CHO 演示行
        self.assertIn("HW350003A", body)
        self.assertIn("HW356009-P1", body)
        self.assertNotIn("CHO01", body)

    def test_stream_four_files_into_monkey_pk(self):
        client = TestClient(app)
        uploaded = _upload_all(client)
        file_ids = [fid for _, fid in uploaded]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "请识别"}],
                "columns": PK_COLS,
                "file_ids": file_ids,
                "table_name": "Monkey PK",
                "auto_skill": True,
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("event: done", body)
        self.assertIn("HW350003A", body)
        self.assertIn("HW356009", body)
        self.assertNotIn("CHO01", body)

    def test_chat_json_keeps_working_for_single_file(self):
        client = TestClient(app)
        path = PK_DIR / "DM-RF-2025022001（HW350003A)DPK检测报告.xlsx"
        with path.open("rb") as f:
            up = client.post("/api/recognize/upload", files={"file": (path.name, f)})
        fid = up.json()["file_id"]
        res = client.post(
            "/api/recognize/chat",
            json={
                "messages": [{"role": "user", "content": "请识别"}],
                "columns": PK_COLS,
                "file_ids": [fid],
                "table_name": "Dog PK",
                "auto_skill": True,
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["rows"])
        self.assertEqual(data["rows"][0]["cpds_id"], "HW350003A")


if __name__ == "__main__":
    unittest.main()
