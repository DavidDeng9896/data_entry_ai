# 导入 Skill 草案（供安装测试）

本目录存放 **可安装到 Data Entry Agent 的 Skill 文稿**。  
每个文件对应一个「实验类型 + 版式/供应商」模板族；安装时把正文导入系统的 Skill（或启用对应 md）。

## 与基线的关系

- 基线：`doc/AI_data_import/baseline-system-prompt.md`（勘查方法，不绑死版式）
- Skill：本目录文件（主源定位、字段映射、过滤、换算）

## 清单

| 文件 | 目标结果表 | 版式指纹 |
| --- | --- | --- |
| `mms-renfu.md` | MMS | 人福 D-RF…-MMS…（Signature/Summary 结构） |
| `mms-3d-biooptima.md` | MMS | 3D BioOptima · Stability in LMs |
| `ppb-renfu.md` | PPB %Fu | 人福 D-RF…-PPB… |
| `ppb-3d-biooptima.md` | PPB %Fu | 3D BioOptima · 蛋白结合率 |
| `cyp-ddi-renfu.md` | CYP inhibition | 人福 D-RF…-DDI… |
| `solubility-pharmaron-rfy.md` | Thermodynamic Solubility | ADME-RFY / Pharmaron Thermodynamic Solubility |
| `hct116-proliferation.md` | SW48/HCT116增殖试验 | HCT116 细胞增殖抑制检测报告 |
| `enzyme-rfp-fi-ic50.md` | Biochemical Activity (ADP-Glo) | RFP WRN ATP preincubation FI_IC50 |
| `herg-rfp.md` | hERG | RFP 手动膜片钳 hERG |
| `pk-precent-winnonlin.md` | Mouse/Rat/Dog PK | 普瑞昇 · 封面/结果汇总/PK参数 |

## 安装测试建议

1. 在系统中新建 Skill，名称用文件标题，内容粘贴 md 正文（可去掉本 README）。
2. 选择匹配的目标结果表，上传对应样例报告，启用该 Skill 后跑识别。
3. 先测「同版式第二份文件」是否仍命中；再测「错版式」是否应换 Skill（例如人福 MMS vs 3D MMS）。

## 尚未覆盖（后续可补）

- Caco-2（3D / 其它供应商）
- CYP 3D 版式
- 溶解度 3D 版式
- 猴 PK 外部报告版式
- 小鼠 PK 3D 版式
- 血浆稳定性 PLS（当前结果表无直接对应）
- CADD 对接/药效团 CSV（当前 17 张结果表无对应）
