# Rules

1. 配置唯一数据源: `configs/platforms.yaml`
2. 新代码导入路径: `platforms/` (禁止 `crawler/`)
3. 修改代码后运行: `pytest tests/test_platform_config.py -v`
4. Git: `<type>: <中文描述>` (type∈{feat,fix,test,docs,refactor,chore})
5. 禁止 `git add .`, 只添加相关文件

# Structure

```
configs/platforms.yaml → src/platform_config.py → platforms/{nvidia,zhipu}/
src/models.py (ModelInfo, TestResult, TestReport)
tests/ (pytest), examples/, scripts/batch_test.py
```

# Commands

```bash
python test_config_quick.py          # 验证配置
pytest tests/test_platform_config.py -v  # 测试
python crawler/main.py -n 10         # 运行
```
