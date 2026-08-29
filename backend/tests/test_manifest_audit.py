from app.agents.manifest import ToolCall, audit_grounded


def _order_lookup(order_number: str, total: float) -> ToolCall:
    return ToolCall(
        name="get_order_status",
        args={"order_number": order_number},
        result={"found": True, "order_number": order_number, "status": "confirmed", "total": total, "currency": "INR"},
    )


class TestAmountFormatting:
    def test_comma_formatted_amount_matches_the_raw_float(self):
        call = _order_lookup("KC4413", 2499.0)
        text = "Your order KC4413 is confirmed, totaling **₹2,499.00**."
        assert audit_grounded(text, [call]) is True

    def test_plain_amount_without_comma_still_matches(self):
        call = _order_lookup("KC4407", 899.0)
        text = "Order KC4407 comes to 899.00 INR."
        assert audit_grounded(text, [call]) is True

    def test_genuinely_wrong_amount_is_still_caught(self):
        call = _order_lookup("KC4413", 2499.0)
        text = "Your order KC4413 comes to ₹9,999.00."
        assert audit_grounded(text, [call]) is False


class TestOrderNumbers:
    def test_real_order_number_passes(self):
        call = _order_lookup("KC4413", 2499.0)
        assert audit_grounded("Your order is KC4413.", [call]) is True

    def test_invented_order_number_is_caught(self):
        call = _order_lookup("KC4413", 2499.0)
        assert audit_grounded("Your order is KC9999.", [call]) is False


class TestNoNumericClaims:
    def test_answer_with_no_numbers_is_trivially_grounded(self):
        call = _order_lookup("KC4413", 2499.0)
        assert audit_grounded("That order is currently confirmed and on its way.", [call]) is True

    def test_list_recent_orders_shape_also_works(self):
        call = ToolCall(
            name="list_recent_orders",
            args={"customer_id": "cust_1056", "limit": 1},
            result={"orders": [{"order_number": "KC4413", "status": "confirmed", "total": 2499.0, "currency": "INR"}]},
        )
        text = "Your most recent order is KC4413, confirmed, totaling ₹2,499.00."
        assert audit_grounded(text, [call]) is True
