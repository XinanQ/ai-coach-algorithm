-- Mock organization data

-- Hierarchy:
-- 1 南京市行 CITY
--   2 鼓楼支行 BRANCH
--     3 鼓楼营业室 OUTLET
--   4 玄武支行 BRANCH
--     5 珠江路网点 OUTLET


INSERT INTO organizations
(id,
 address,
 code,
 description,
 level,
 name,
 phone,
 parent_id)


VALUES
    (1, '南京市玄武区中山东路1号', 'ORG0001', '南京市级管理机构', 'CITY', '南京市行', '025-80000001', NULL),
    (2, '南京市鼓楼区中央路88号', 'ORG0002', '南京市行下属鼓楼支行', 'BRANCH', '鼓楼支行', '025-80000002', 1),
    (3, '南京市鼓楼区中央路88号一楼', 'ORG0003', '鼓楼支行下属营业网点', 'OUTLET', '鼓楼营业室', '025-80000003', 2),
    (4, '南京市玄武区珠江路99号', 'ORG0004', '南京市行下属玄武支行', 'BRANCH', '玄武支行', '025-80000004', 1),
    (5, '南京市玄武区珠江路168号', 'ORG0005', '玄武支行下属营业网点', 'OUTLET', '珠江路网点', '025-80000005', 4);
