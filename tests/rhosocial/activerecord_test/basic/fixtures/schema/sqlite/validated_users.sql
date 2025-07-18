-- tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/validated_users.sql
CREATE TABLE validated_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,  -- 长度3-50的字符串，只能包含字母和数字
    email TEXT NOT NULL,     -- 有效的邮箱格式
    age INTEGER             -- 可选，但如果提供必须在0-150之间，且不小于13
);