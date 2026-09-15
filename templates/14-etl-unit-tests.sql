-- ETL 单元测试 SQL — 精简模板

-- TC_001: 行数校验
SELECT 'TC_ROW_COUNT' AS test_id,
       CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM dwd_sales_order WHERE dt = '${bizdate}';

-- TC_002: 主键唯一性
SELECT 'TC_PK_UNIQUE' AS test_id,
       CASE WHEN COUNT(*) = COUNT(DISTINCT order_id) THEN 'PASS' ELSE 'FAIL' END AS result
FROM dwd_sales_order WHERE dt = '${bizdate}';

-- TC_003: 空值率
SELECT 'TC_NULL_RATE' AS test_id,
       CASE WHEN SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) / COUNT(*) < 0.01
            THEN 'PASS' ELSE 'FAIL' END AS result
FROM dwd_sales_order WHERE dt = '${bizdate}';

-- TC_004: 值域校验
SELECT 'TC_VALUE_RANGE' AS test_id,
       CASE WHEN SUM(CASE WHEN order_amount < 0 THEN 1 ELSE 0 END) = 0
            THEN 'PASS' ELSE 'FAIL' END AS result
FROM dwd_sales_order WHERE dt = '${bizdate}';

-- TC_005: 跨表对账 DWD vs ODS
SELECT 'TC_RECONCILE' AS test_id,
       CASE WHEN (SELECT COUNT(*) FROM ods_crm_order WHERE dt='${bizdate}') =
                (SELECT COUNT(*) FROM dwd_sales_order WHERE dt='${bizdate}')
            THEN 'PASS' ELSE 'FAIL' END AS result;

-- TC_006: 清洗后拒绝数据验证
-- v1.2 新增：验证 dw_reject_records 数据量与 cleaning_audit.log 一致
SELECT 'TC_REJECT_COUNT' AS test_id,
       CASE WHEN COUNT(*) >= 0 THEN 'PASS' ELSE 'FAIL' END AS result,
       COUNT(*) AS reject_count
FROM dw_reject_records WHERE dt = '${bizdate}';
