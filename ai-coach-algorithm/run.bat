.\.venv\Scripts\python.exe -m app.core.intent_dataset_prep --input data/intent_eval_gold.jsonl

# 标定意图存在阈值（扫阈值找最优 micro-F1）
.\.venv\Scripts\python.exe -m app.core.intent_threshold_calibrator --input data/intent_eval_gold.jsonl

# 训练 BERT-mini 多标签分类头（产出 models/bert_mini_intent/）
.\.venv\Scripts\python.exe -m app.core.bert_mini_trainer --train-file data/intent_train.jsonl

# 对比 keyword baseline vs BERT-mini 在 eval 集上的 F1
.\.venv\Scripts\python.exe -m app.core.intent_model_eval