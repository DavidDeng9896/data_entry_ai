# 英佰CRO模板

适用于英佰 CRO 交付的 Binding Assay 实验报告（Excel/PDF）。

## 列映射规则
- `cell_line`：对应源文件中 "Cell Line"、"细胞系"、"Cell" 等列，取原始编号（如 CHO01）。
- `antibody`：对应 "Antibody"、"抗体"、"Ab" 等列，保留原始编号（如 AB023-001）。
- `cell_type`：对应 "Cell Type"、"细胞类型" 列，多个值用英文逗号连接。
- `condition`：实验条件，通常为 Experimental / Control。
- `concentration`：浓度，单位 ug/ml，只保留数值，去掉单位。
- `response`：响应值 RU，保留两位小数。
- `inhibition`：抑制常数，保留数值。
- `remark`：备注/用途说明，原样保留中文。

## 注意事项
- 源文件常见多级表头和合并单元格，以数据区为准。
- 单位换算：ng/ml → ug/ml 需除以 1000。
- 空行和汇总行（Total、Mean 等）忽略。
