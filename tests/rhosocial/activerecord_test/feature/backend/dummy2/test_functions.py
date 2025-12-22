"""
Tests for the SQL function factory functions in functions.py
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, count, sum_, avg, min_, max_,
    lower, upper, concat, coalesce, length, substring, 
    replace, initcap, left, right, lpad, rpad, reverse, strpos,
    abs_, round_, ceil, floor, sqrt, power, exp, log, sin, cos, tan,
    now, current_date, current_time, year, month, day, hour, minute, second,
    date_part, date_trunc, nullif, greatest, least, case,
    row_number, rank, dense_rank, lag, lead, first_value, last_value, nth_value,
    json_extract, json_extract_text, json_build_object, json_array_elements,
    array_agg, unnest, array_length, cast, to_char, to_number, to_date,
    trim
)
from rhosocial.activerecord.backend.expression.operators import RawSQLExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestAggregateFunctionFactories:
    """Tests for aggregate function factories."""
    
    def test_count_star(self, dummy_dialect: DummyDialect):
        """Test COUNT(*) function."""
        func = count(dummy_dialect)
        sql, params = func.to_sql()
        assert "COUNT(*)" in sql
        assert params == ()
    
    def test_count_with_column(self, dummy_dialect: DummyDialect):
        """Test COUNT(column) function."""
        func = count(dummy_dialect, "id")
        sql, params = func.to_sql()
        assert "COUNT(" in sql
        assert params == ()
    
    def test_count_with_expression(self, dummy_dialect: DummyDialect):
        """Test COUNT with expression."""
        col = Column(dummy_dialect, "name")
        func = count(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "COUNT(" in sql
        assert '"name"' in sql  # Should contain the quoted column name
    
    def test_count_distinct(self, dummy_dialect: DummyDialect):
        """Test COUNT(DISTINCT ...) function."""
        func = count(dummy_dialect, "id", is_distinct=True)
        sql, params = func.to_sql()
        assert "COUNT(DISTINCT" in sql
    
    def test_count_with_alias(self, dummy_dialect: DummyDialect):
        """Test COUNT with alias."""
        func = count(dummy_dialect, "id", alias="total")
        sql, params = func.to_sql()
        assert "AS" in sql
    
    def test_sum_function(self, dummy_dialect: DummyDialect):
        """Test SUM function."""
        func = sum_(dummy_dialect, "amount")
        sql, params = func.to_sql()
        assert "SUM(" in sql
        assert params == ()
    
    def test_sum_with_expression(self, dummy_dialect: DummyDialect):
        """Test SUM with expression."""
        col = Column(dummy_dialect, "price")
        func = sum_(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "SUM(" in sql
        assert '"price"' in sql
    
    def test_sum_distinct(self, dummy_dialect: DummyDialect):
        """Test SUM(DISTINCT ...) function."""
        func = sum_(dummy_dialect, "amount", is_distinct=True)
        sql, params = func.to_sql()
        assert "SUM(DISTINCT" in sql
    
    def test_avg_function(self, dummy_dialect: DummyDialect):
        """Test AVG function."""
        func = avg(dummy_dialect, "score")
        sql, params = func.to_sql()
        assert "AVG(" in sql
    
    def test_min_function(self, dummy_dialect: DummyDialect):
        """Test MIN function."""
        func = min_(dummy_dialect, "age")
        sql, params = func.to_sql()
        assert "MIN(" in sql
    
    def test_max_function(self, dummy_dialect: DummyDialect):
        """Test MAX function."""
        func = max_(dummy_dialect, "salary")
        sql, params = func.to_sql()
        assert "MAX(" in sql


class TestScalarFunctionFactories:
    """Tests for scalar function factories."""
    
    def test_lower_function(self, dummy_dialect: DummyDialect):
        """Test LOWER function."""
        func = lower(dummy_dialect, "name")
        sql, params = func.to_sql()
        assert "LOWER(" in sql
        assert params == ("name",)
    
    def test_upper_function(self, dummy_dialect: DummyDialect):
        """Test UPPER function."""
        func = upper(dummy_dialect, "name")
        sql, params = func.to_sql()
        assert "UPPER(" in sql
    
    def test_concat_function(self, dummy_dialect: DummyDialect):
        """Test CONCAT function."""
        func = concat(dummy_dialect, "first_name", "last_name")
        sql, params = func.to_sql()
        assert "CONCAT(" in sql
        assert params == ("first_name", "last_name")
    
    def test_concat_with_expressions(self, dummy_dialect: DummyDialect):
        """Test CONCAT with expression arguments."""
        col1 = Column(dummy_dialect, "first_name")
        col2 = Column(dummy_dialect, "last_name")
        func = concat(dummy_dialect, col1, col2)
        sql, params = func.to_sql()
        assert "CONCAT(" in sql
        assert '"first_name"' in sql
        assert '"last_name"' in sql
    
    def test_coalesce_function(self, dummy_dialect: DummyDialect):
        """Test COALESCE function."""
        func = coalesce(dummy_dialect, "name", "default_value")
        sql, params = func.to_sql()
        assert "COALESCE(" in sql
    
    def test_coalesce_with_expressions(self, dummy_dialect: DummyDialect):
        """Test COALESCE with expression arguments."""
        col1 = Column(dummy_dialect, "first_name")
        col2 = Column(dummy_dialect, "last_name")
        func = coalesce(dummy_dialect, col1, col2)
        sql, params = func.to_sql()
        assert "COALESCE(" in sql


class TestStringFunctionFactories:
    """Tests for string function factories."""
    
    def test_length_function(self, dummy_dialect: DummyDialect):
        """Test LENGTH function."""
        func = length(dummy_dialect, "name")
        sql, params = func.to_sql()
        assert "LENGTH(" in sql
    
    def test_substring_function(self, dummy_dialect: DummyDialect):
        """Test SUBSTRING function."""
        func = substring(dummy_dialect, "text", 1, 5)
        sql, params = func.to_sql()
        assert "SUBSTRING(" in sql
        assert params == ("text", 1, 5)
    
    def test_substring_without_length(self, dummy_dialect: DummyDialect):
        """Test SUBSTRING function without length parameter."""
        func = substring(dummy_dialect, "text", 1)
        sql, params = func.to_sql()
        assert "SUBSTRING(" in sql
        assert params == ("text", 1)
    
    def test_trim_function_default(self, dummy_dialect: DummyDialect):
        """Test TRIM function with default direction."""
        func = trim(dummy_dialect, "name")
        sql, params = func.to_sql()
        assert isinstance(func, RawSQLExpression)
        assert "TRIM(BOTH FROM" in sql
    
    def test_trim_function_with_chars(self, dummy_dialect: DummyDialect):
        """Test TRIM function with specific characters."""
        func = trim(dummy_dialect, "name", " ", "LEADING")
        sql, params = func.to_sql()
        assert "TRIM(LEADING" in sql
    
    def test_replace_function(self, dummy_dialect: DummyDialect):
        """Test REPLACE function."""
        func = replace(dummy_dialect, "text", "old", "new")
        sql, params = func.to_sql()
        assert "REPLACE(" in sql
        assert params == ("text", "old", "new")
    
    def test_initcap_function(self, dummy_dialect: DummyDialect):
        """Test INITCAP function."""
        func = initcap(dummy_dialect, "name")
        sql, params = func.to_sql()
        assert "INITCAP(" in sql
    
    def test_left_function(self, dummy_dialect: DummyDialect):
        """Test LEFT function."""
        func = left(dummy_dialect, "text", 5)
        sql, params = func.to_sql()
        assert "LEFT(" in sql
        assert params == ("text", 5)
    
    def test_right_function(self, dummy_dialect: DummyDialect):
        """Test RIGHT function."""
        func = right(dummy_dialect, "text", 5)
        sql, params = func.to_sql()
        assert "RIGHT(" in sql
        assert params == ("text", 5)
    
    def test_lpad_function(self, dummy_dialect: DummyDialect):
        """Test LPAD function."""
        func = lpad(dummy_dialect, "text", 10, "0")
        sql, params = func.to_sql()
        assert "LPAD(" in sql
        assert params == ("text", 10, "0")
    
    def test_lpad_function_without_pad(self, dummy_dialect: DummyDialect):
        """Test LPAD function without pad character."""
        func = lpad(dummy_dialect, "text", 10)
        sql, params = func.to_sql()
        assert "LPAD(" in sql
        assert params == ("text", 10)
    
    def test_rpad_function(self, dummy_dialect: DummyDialect):
        """Test RPAD function."""
        func = rpad(dummy_dialect, "text", 10, "0")
        sql, params = func.to_sql()
        assert "RPAD(" in sql
        assert params == ("text", 10, "0")
    
    def test_reverse_function(self, dummy_dialect: DummyDialect):
        """Test REVERSE function."""
        func = reverse(dummy_dialect, "text")
        sql, params = func.to_sql()
        assert "REVERSE(" in sql
    
    def test_strpos_function(self, dummy_dialect: DummyDialect):
        """Test STRPOS function."""
        func = strpos(dummy_dialect, "text", "substring")
        sql, params = func.to_sql()
        assert "STRPOS(" in sql
        assert params == ("text", "substring")


class TestMathFunctionFactories:
    """Tests for math function factories."""
    
    def test_abs_function(self, dummy_dialect: DummyDialect):
        """Test ABS function."""
        func = abs_(dummy_dialect, -5)
        sql, params = func.to_sql()
        assert "ABS(" in sql
    
    def test_round_function(self, dummy_dialect: DummyDialect):
        """Test ROUND function."""
        func = round_(dummy_dialect, 3.14159)
        sql, params = func.to_sql()
        assert "ROUND(" in sql
    
    def test_round_function_with_decimals(self, dummy_dialect: DummyDialect):
        """Test ROUND function with decimal places."""
        func = round_(dummy_dialect, 3.14159, 2)
        sql, params = func.to_sql()
        assert "ROUND(" in sql
        assert params == (3.14159, 2)
    
    def test_ceil_function(self, dummy_dialect: DummyDialect):
        """Test CEIL function."""
        func = ceil(dummy_dialect, 3.14)
        sql, params = func.to_sql()
        assert "CEIL(" in sql
    
    def test_floor_function(self, dummy_dialect: DummyDialect):
        """Test FLOOR function."""
        func = floor(dummy_dialect, 3.99)
        sql, params = func.to_sql()
        assert "FLOOR(" in sql
    
    def test_sqrt_function(self, dummy_dialect: DummyDialect):
        """Test SQRT function."""
        func = sqrt(dummy_dialect, 16)
        sql, params = func.to_sql()
        assert "SQRT(" in sql
    
    def test_power_function(self, dummy_dialect: DummyDialect):
        """Test POWER function."""
        func = power(dummy_dialect, 2, 3)
        sql, params = func.to_sql()
        assert "POWER(" in sql
        assert params == (2, 3)
    
    def test_exp_function(self, dummy_dialect: DummyDialect):
        """Test EXP function."""
        func = exp(dummy_dialect, 1)
        sql, params = func.to_sql()
        assert "EXP(" in sql
    
    def test_log_function(self, dummy_dialect: DummyDialect):
        """Test LOG function."""
        func = log(dummy_dialect, 10)
        sql, params = func.to_sql()
        assert "LOG(" in sql
    
    def test_log_function_with_base(self, dummy_dialect: DummyDialect):
        """Test LOG function with base."""
        func = log(dummy_dialect, 100, 10)
        sql, params = func.to_sql()
        assert "LOG(" in sql
        assert params == (100, 10)
    
    def test_trigonometric_functions(self, dummy_dialect: DummyDialect):
        """Test trigonometric functions."""
        sin_func = sin(dummy_dialect, 0)
        cos_func = cos(dummy_dialect, 0)
        tan_func = tan(dummy_dialect, 0)
        
        sin_sql, sin_params = sin_func.to_sql()
        cos_sql, cos_params = cos_func.to_sql()
        tan_sql, tan_params = tan_func.to_sql()
        
        assert "SIN(" in sin_sql
        assert "COS(" in cos_sql
        assert "TAN(" in tan_sql


class TestDateTimeFunctionFactories:
    """Tests for date/time function factories."""
    
    def test_now_function(self, dummy_dialect: DummyDialect):
        """Test NOW function."""
        func = now(dummy_dialect)
        sql, params = func.to_sql()
        assert "NOW(" in sql
    
    def test_current_date_function(self, dummy_dialect: DummyDialect):
        """Test CURRENT_DATE function."""
        func = current_date(dummy_dialect)
        sql, params = func.to_sql()
        assert "CURRENT_DATE" in sql
    
    def test_current_time_function(self, dummy_dialect: DummyDialect):
        """Test CURRENT_TIME function."""
        func = current_time(dummy_dialect)
        sql, params = func.to_sql()
        assert "CURRENT_TIME" in sql
    
    def test_date_part_functions(self, dummy_dialect: DummyDialect):
        """Test YEAR, MONTH, DAY, HOUR, MINUTE, SECOND functions."""
        date_col = Column(dummy_dialect, "created_at")
        
        year_func = year(dummy_dialect, date_col)
        month_func = month(dummy_dialect, date_col)
        day_func = day(dummy_dialect, date_col)
        hour_func = hour(dummy_dialect, date_col)
        minute_func = minute(dummy_dialect, date_col)
        second_func = second(dummy_dialect, date_col)
        
        year_sql, year_params = year_func.to_sql()
        month_sql, month_params = month_func.to_sql()
        day_sql, day_params = day_func.to_sql()
        hour_sql, hour_params = hour_func.to_sql()
        minute_sql, minute_params = minute_func.to_sql()
        second_sql, second_params = second_func.to_sql()
        
        assert "YEAR(" in year_sql
        assert "MONTH(" in month_sql
        assert "DAY(" in day_sql
        assert "HOUR(" in hour_sql
        assert "MINUTE(" in minute_sql
        assert "SECOND(" in second_sql
    
    def test_date_part_function(self, dummy_dialect: DummyDialect):
        """Test DATE_PART function."""
        func = date_part(dummy_dialect, "year", "created_at")
        sql, params = func.to_sql()
        assert "DATE_PART(" in sql
        assert params == ("year",)
    
    def test_date_trunc_function(self, dummy_dialect: DummyDialect):
        """Test DATE_TRUNC function."""
        func = date_trunc(dummy_dialect, "month", "created_at")
        sql, params = func.to_sql()
        assert "DATE_TRUNC(" in sql
        assert params == ("month",)


class TestConditionalFunctionFactories:
    """Tests for conditional function factories."""
    
    def test_case_function(self, dummy_dialect: DummyDialect):
        """Test CASE function."""
        func = case(dummy_dialect)
        assert func.dialect is dummy_dialect
        # The CaseExpression class is tested in other test files
    
    def test_case_with_alias(self, dummy_dialect: DummyDialect):
        """Test CASE function with alias."""
        func = case(dummy_dialect, alias="status_label")
        assert func.alias == "status_label"
    
    def test_nullif_function(self, dummy_dialect: DummyDialect):
        """Test NULLIF function."""
        func = nullif(dummy_dialect, "value", "null_value")
        sql, params = func.to_sql()
        assert "NULLIF(" in sql
    
    def test_greatest_function(self, dummy_dialect: DummyDialect):
        """Test GREATEST function."""
        func = greatest(dummy_dialect, "a", "b", "c")
        sql, params = func.to_sql()
        assert "GREATEST(" in sql
    
    def test_least_function(self, dummy_dialect: DummyDialect):
        """Test LEAST function."""
        func = least(dummy_dialect, "a", "b", "c")
        sql, params = func.to_sql()
        assert "LEAST(" in sql


class TestWindowFunctionFactories:
    """Tests for window function factories."""
    
    def test_row_number_function(self, dummy_dialect: DummyDialect):
        """Test ROW_NUMBER function."""
        func = row_number(dummy_dialect)
        sql, params = func.to_sql()
        assert "ROW_NUMBER(" in sql
    
    def test_rank_functions(self, dummy_dialect: DummyDialect):
        """Test RANK and DENSE_RANK functions."""
        rank_func = rank(dummy_dialect)
        dense_rank_func = dense_rank(dummy_dialect)
        
        rank_sql, rank_params = rank_func.to_sql()
        dense_rank_sql, dense_rank_params = dense_rank_func.to_sql()
        
        assert "RANK(" in rank_sql
        assert "DENSE_RANK(" in dense_rank_sql
    
    def test_lag_function(self, dummy_dialect: DummyDialect):
        """Test LAG function."""
        func = lag(dummy_dialect, "value", 1, "default")
        sql, params = func.to_sql()
        assert "LAG(" in sql
        # The exact structure depends on how the dialect formats window functions
    
    def test_lead_function(self, dummy_dialect: DummyDialect):
        """Test LEAD function."""
        func = lead(dummy_dialect, "value", 1, "default")
        sql, params = func.to_sql()
        assert "LEAD(" in sql
    
    def test_value_functions(self, dummy_dialect: DummyDialect):
        """Test FIRST_VALUE, LAST_VALUE, NTH_VALUE functions."""
        first_func = first_value(dummy_dialect, "value")
        last_func = last_value(dummy_dialect, "value")
        nth_func = nth_value(dummy_dialect, "value", 2)
        
        first_sql, first_params = first_func.to_sql()
        last_sql, last_params = last_func.to_sql()
        nth_sql, nth_params = nth_func.to_sql()
        
        assert "FIRST_VALUE(" in first_sql
        assert "LAST_VALUE(" in last_sql
        assert "NTH_VALUE(" in nth_sql


class TestJsonFunctionFactories:
    """Tests for JSON function factories."""
    
    def test_json_extract_functions(self, dummy_dialect: DummyDialect):
        """Test JSON extract functions."""
        col = Column(dummy_dialect, "json_data")
        
        extract_func = json_extract(dummy_dialect, col, "$.name")
        extract_text_func = json_extract_text(dummy_dialect, col, "$.name")
        
        extract_sql, extract_params = extract_func.to_sql()
        extract_text_sql, extract_text_params = extract_text_func.to_sql()
        
        # The exact SQL depends on the dialect implementation
        assert extract_func.operation == "->"
        assert extract_text_func.operation == "->>"
    
    def test_json_build_object_function(self, dummy_dialect: DummyDialect):
        """Test JSON_BUILD_OBJECT function."""
        func = json_build_object(dummy_dialect, "key1", "value1", "key2", "value2")
        sql, params = func.to_sql()
        assert "JSON_BUILD_OBJECT(" in sql
    
    def test_json_array_elements_function(self, dummy_dialect: DummyDialect):
        """Test JSON_ARRAY_ELEMENTS function."""
        func = json_array_elements(dummy_dialect, "json_array")
        sql, params = func.to_sql()
        assert "JSON_ARRAY_ELEMENTS(" in sql


class TestArrayFunctionFactories:
    """Tests for array function factories."""
    
    def test_array_agg_function(self, dummy_dialect: DummyDialect):
        """Test ARRAY_AGG function."""
        func = array_agg(dummy_dialect, "value", is_distinct=True, alias="agg_array")
        sql, params = func.to_sql()
        assert "ARRAY_AGG(" in sql
    
    def test_unnest_function(self, dummy_dialect: DummyDialect):
        """Test UNNEST function."""
        func = unnest(dummy_dialect, "array_col")
        sql, params = func.to_sql()
        assert "UNNEST(" in sql
    
    def test_array_length_function(self, dummy_dialect: DummyDialect):
        """Test ARRAY_LENGTH function."""
        func = array_length(dummy_dialect, "array_col", 1)
        sql, params = func.to_sql()
        assert "ARRAY_LENGTH(" in sql
        assert params == (1,)


class TestTypeConversionFunctionFactories:
    """Tests for type conversion function factories."""
    
    def test_cast_function(self, dummy_dialect: DummyDialect):
        """Test CAST function."""
        func = cast(dummy_dialect, "value", "INTEGER")
        assert func.target_type == "INTEGER"
        sql, params = func.to_sql()
        assert "CAST(" in sql
    
    def test_to_char_function(self, dummy_dialect: DummyDialect):
        """Test TO_CHAR function."""
        func = to_char(dummy_dialect, "value", "YYYY-MM-DD")
        sql, params = func.to_sql()
        assert "TO_CHAR(" in sql
        assert params == ("YYYY-MM-DD",)
    
    def test_to_char_function_without_format(self, dummy_dialect: DummyDialect):
        """Test TO_CHAR function without format."""
        func = to_char(dummy_dialect, "value")
        sql, params = func.to_sql()
        assert "TO_CHAR(" in sql
        assert params == ()
    
    def test_to_number_function(self, dummy_dialect: DummyDialect):
        """Test TO_NUMBER function."""
        func = to_number(dummy_dialect, "value", "9999")
        sql, params = func.to_sql()
        assert "TO_NUMBER(" in sql
        assert params == ("9999",)

    def test_to_number_function_without_format(self, dummy_dialect: DummyDialect):
        """Test TO_NUMBER function without format."""
        func = to_number(dummy_dialect, "value")
        sql, params = func.to_sql()
        assert "TO_NUMBER(" in sql
        assert params == ()
    
    def test_to_date_function(self, dummy_dialect: DummyDialect):
        """Test TO_DATE function."""
        func = to_date(dummy_dialect, "value", "YYYY-MM-DD")
        sql, params = func.to_sql()
        assert "TO_DATE(" in sql
        assert params == ("YYYY-MM-DD",)

    def test_to_date_function_without_format(self, dummy_dialect: DummyDialect):
        """Test TO_DATE function without format."""
        func = to_date(dummy_dialect, "value")
        sql, params = func.to_sql()
        assert "TO_DATE(" in sql
        assert params == ()


class TestMathFunctionFactoriesExtended:
    """Additional tests for math function factories."""

    def test_sin_function(self, dummy_dialect: DummyDialect):
        """Test SIN function."""
        func = sin(dummy_dialect, "angle")
        sql, params = func.to_sql()
        assert "SIN(" in sql
        # When passing string to sin, it's treated as a column name, so no parameters
        assert params == ()

    def test_cos_function(self, dummy_dialect: DummyDialect):
        """Test COS function."""
        func = cos(dummy_dialect, "angle")
        sql, params = func.to_sql()
        assert "COS(" in sql
        # When passing string to cos, it's treated as a column name, so no parameters
        assert params == ()

    def test_tan_function(self, dummy_dialect: DummyDialect):
        """Test TAN function."""
        func = tan(dummy_dialect, "angle")
        sql, params = func.to_sql()
        assert "TAN(" in sql
        # When passing string to tan, it's treated as a column name, so no parameters
        assert params == ()


class TestDateTimeFunctionFactoriesExtended:
    """Additional tests for date/time function factories."""

    def test_year_function(self, dummy_dialect: DummyDialect):
        """Test YEAR function."""
        func = year(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "YEAR(" in sql
        # When passing string to year, it's treated as a column name, so no parameters
        assert params == ()

    def test_month_function(self, dummy_dialect: DummyDialect):
        """Test MONTH function."""
        func = month(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "MONTH(" in sql
        # When passing string to month, it's treated as a column name, so no parameters
        assert params == ()

    def test_day_function(self, dummy_dialect: DummyDialect):
        """Test DAY function."""
        func = day(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "DAY(" in sql
        # When passing string to day, it's treated as a column name, so no parameters
        assert params == ()

    def test_hour_function(self, dummy_dialect: DummyDialect):
        """Test HOUR function."""
        func = hour(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "HOUR(" in sql
        # When passing string to hour, it's treated as a column name, so no parameters
        assert params == ()

    def test_minute_function(self, dummy_dialect: DummyDialect):
        """Test MINUTE function."""
        func = minute(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "MINUTE(" in sql
        # When passing string to minute, it's treated as a column name, so no parameters
        assert params == ()

    def test_second_function(self, dummy_dialect: DummyDialect):
        """Test SECOND function."""
        func = second(dummy_dialect, "created_at")
        sql, params = func.to_sql()
        assert "SECOND(" in sql
        # When passing string to second, it's treated as a column name, so no parameters
        assert params == ()


class TestConditionalFunctionFactoriesExtended:
    """Additional tests for conditional function factories."""

    def test_nullif_function(self, dummy_dialect: DummyDialect):
        """Test NULLIF function."""
        func = nullif(dummy_dialect, "value", "null_value")
        sql, params = func.to_sql()
        assert "NULLIF(" in sql
        assert params == ("value", "null_value")

    def test_greatest_function(self, dummy_dialect: DummyDialect):
        """Test GREATEST function."""
        func = greatest(dummy_dialect, "a", "b", "c")
        sql, params = func.to_sql()
        assert "GREATEST(" in sql
        assert params == ("a", "b", "c")

    def test_least_function(self, dummy_dialect: DummyDialect):
        """Test LEAST function."""
        func = least(dummy_dialect, "a", "b", "c")
        sql, params = func.to_sql()
        assert "LEAST(" in sql
        assert params == ("a", "b", "c")


class TestWindowFunctionFactoriesExtended:
    """Additional tests for window function factories."""

    def test_row_number_with_alias(self, dummy_dialect: DummyDialect):
        """Test ROW_NUMBER function with alias."""
        func = row_number(dummy_dialect, alias="row_num")
        sql, params = func.to_sql()
        assert "ROW_NUMBER(" in sql
        assert "AS" in sql

    def test_rank_with_alias(self, dummy_dialect: DummyDialect):
        """Test RANK function with alias."""
        func = rank(dummy_dialect, alias="rank_val")
        sql, params = func.to_sql()
        assert "RANK(" in sql
        assert "AS" in sql

    def test_dense_rank_with_alias(self, dummy_dialect: DummyDialect):
        """Test DENSE_RANK function with alias."""
        func = dense_rank(dummy_dialect, alias="dense_rank_val")
        sql, params = func.to_sql()
        assert "DENSE_RANK(" in sql
        assert "AS" in sql

    def test_lag_function_with_offset_and_default(self, dummy_dialect: DummyDialect):
        """Test LAG function with offset and default value."""
        func = lag(dummy_dialect, "value", 2, "default")
        sql, params = func.to_sql()
        assert "LAG(" in sql
        # When passing "value" as string, it's treated as column, but 2 and "default" are literals
        # So parameters should be (2, "default")
        assert params == (2, "default")

    def test_lag_function_without_default(self, dummy_dialect: DummyDialect):
        """Test LAG function without default value."""
        func = lag(dummy_dialect, "value", 1)  # No default provided
        sql, params = func.to_sql()
        assert "LAG(" in sql
        # When passing "value" as string, it's treated as column, but only 1 is literal
        # So parameters should be (1,)
        assert params == (1,)

    def test_lead_function_with_offset_and_default(self, dummy_dialect: DummyDialect):
        """Test LEAD function with offset and default value."""
        func = lead(dummy_dialect, "value", 2, "default")
        sql, params = func.to_sql()
        assert "LEAD(" in sql
        # When passing "value" as string, it's treated as column, but 2 and "default" are literals
        # So parameters should be (2, "default")
        assert params == (2, "default")

    def test_lead_function_without_default(self, dummy_dialect: DummyDialect):
        """Test LEAD function without default value."""
        func = lead(dummy_dialect, "value", 1)  # No default provided
        sql, params = func.to_sql()
        assert "LEAD(" in sql
        # When passing "value" as string, it's treated as column, but only 1 is literal
        # So parameters should be (1,)
        assert params == (1,)

    def test_first_value_function(self, dummy_dialect: DummyDialect):
        """Test FIRST_VALUE function."""
        func = first_value(dummy_dialect, "value", alias="first_val")
        sql, params = func.to_sql()
        assert "FIRST_VALUE(" in sql
        assert "AS" in sql
        # When passing "value" as string, it's treated as column, so no parameters
        assert params == ()

    def test_last_value_function(self, dummy_dialect: DummyDialect):
        """Test LAST_VALUE function."""
        func = last_value(dummy_dialect, "value", alias="last_val")
        sql, params = func.to_sql()
        assert "LAST_VALUE(" in sql
        assert "AS" in sql
        # When passing "value" as string, it's treated as column, so no parameters
        assert params == ()

    def test_nth_value_function(self, dummy_dialect: DummyDialect):
        """Test NTH_VALUE function."""
        func = nth_value(dummy_dialect, "value", 3, alias="nth_val")
        sql, params = func.to_sql()
        assert "NTH_VALUE(" in sql
        assert "AS" in sql
        # When passing "value" as string, it's treated as column, but 3 is literal
        # So parameters should be (3,)
        assert params == (3,)


class TestJsonFunctionFactoriesExtended:
    """Additional tests for JSON function factories."""

    def test_json_extract_function(self, dummy_dialect: DummyDialect):
        """Test JSON extract function."""
        col = Column(dummy_dialect, "json_col")
        func = json_extract(dummy_dialect, col, "$.name")
        sql, params = func.to_sql()
        assert func.operation == "->"
        assert '"json_col"' in sql or "json_col" in sql

    def test_json_extract_text_function(self, dummy_dialect: DummyDialect):
        """Test JSON extract text function."""
        col = Column(dummy_dialect, "json_col")
        func = json_extract_text(dummy_dialect, col, "$.name")
        sql, params = func.to_sql()
        assert func.operation == "->>"
        assert '"json_col"' in sql or "json_col" in sql

    def test_json_build_object_function(self, dummy_dialect: DummyDialect):
        """Test JSON_BUILD_OBJECT function."""
        func = json_build_object(dummy_dialect, "key1", "value1", "key2", "value2")
        sql, params = func.to_sql()
        assert "JSON_BUILD_OBJECT(" in sql
        assert params == ("key1", "value1", "key2", "value2")

    def test_json_array_elements_function(self, dummy_dialect: DummyDialect):
        """Test JSON_ARRAY_ELEMENTS function."""
        func = json_array_elements(dummy_dialect, "json_array")
        sql, params = func.to_sql()
        assert "JSON_ARRAY_ELEMENTS(" in sql
        # When passing "json_array" as string, it's treated as a column name, so no parameters
        assert params == ()