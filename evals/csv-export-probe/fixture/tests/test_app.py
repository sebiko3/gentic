import unittest

from app import ORDERS, USERS, render_table, route


class Routes(unittest.TestCase):
    def test_users_table_renders_every_column(self):
        status, _, body = route("/admin/users")
        self.assertEqual(status, 200)
        for column in USERS[0]:
            self.assertIn(f"<th>{column}</th>", body)

    def test_orders_table_has_one_row_per_order(self):
        status, _, body = route("/admin/orders")
        self.assertEqual(status, 200)
        self.assertEqual(body.count("<tr>"), len(ORDERS) + 1)

    def test_unknown_path_is_404(self):
        self.assertEqual(route("/admin/secrets")[0], 404)

    def test_empty_table(self):
        self.assertEqual(render_table([]), "<table></table>")
