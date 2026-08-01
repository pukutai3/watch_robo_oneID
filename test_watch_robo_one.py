import os
import unittest
from unittest.mock import call, patch

import watch_robo_one as watcher


class WatchRoboOneTests(unittest.TestCase):
    def test_extract_latest_robot_id_uses_highest_id(self) -> None:
        html = """
        <a href="/rankings/view/1965">A</a>
        <a href="/rankings/view/1966">B</a>
        """

        self.assertEqual(watcher.extract_latest_robot_id(html), 1966)

    def test_extract_latest_robot_id_rejects_unexpected_page(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "No robot IDs found"):
            watcher.extract_latest_robot_id("<html></html>")

    @patch("watch_robo_one.fetch_url")
    def test_fetch_latest_robot_id_reads_last_search_page(self, fetch_url) -> None:
        fetch_url.side_effect = [
            '<a href="/rankings/search/page:87">87</a>',
            '<a href="/rankings/view/1966">latest</a>',
        ]

        self.assertEqual(watcher.fetch_latest_robot_id(timeout=20), 1966)
        self.assertEqual(
            fetch_url.call_args_list,
            [
                call(watcher.SEARCH_URL, timeout=20),
                call(f"{watcher.SEARCH_URL}page:87", timeout=20),
            ],
        )

    @patch("watch_robo_one.fetch_robot_page")
    def test_scan_checks_entire_known_id_range(self, fetch_robot_page) -> None:
        fetch_robot_page.side_effect = lambda robot_id, timeout: watcher.RobotPage(
            robot_id=robot_id,
            exists=robot_id == 23,
        )

        pages = watcher.scan_for_new_pages(1, 23, timeout=20)

        self.assertEqual([page.robot_id for page in pages], [23])
        self.assertEqual(fetch_robot_page.call_count, 22)

    @patch("watch_robo_one.save_state")
    @patch("watch_robo_one.notify")
    def test_process_new_pages_checkpoints_each_notification(
        self, notify, save_state
    ) -> None:
        state = {"last_seen_id": 1}
        saved_ids: list[int] = []
        save_state.side_effect = lambda value: saved_ids.append(value["last_seen_id"])
        pages = [
            watcher.RobotPage(robot_id=2, exists=True),
            watcher.RobotPage(robot_id=4, exists=True),
        ]

        watcher.process_new_pages(pages, state, timeout=20)

        self.assertEqual(notify.call_count, 2)
        self.assertEqual(saved_ids, [2, 4])
        self.assertEqual(state["last_seen_id"], 4)

    @patch("watch_robo_one.save_state")
    @patch("watch_robo_one.notify")
    def test_process_new_pages_keeps_completed_checkpoint_on_failure(
        self, notify, save_state
    ) -> None:
        state = {"last_seen_id": 1}
        saved_ids: list[int] = []
        save_state.side_effect = lambda value: saved_ids.append(value["last_seen_id"])
        notify.side_effect = [None, RuntimeError("webhook failed")]
        pages = [
            watcher.RobotPage(robot_id=2, exists=True),
            watcher.RobotPage(robot_id=4, exists=True),
        ]

        with self.assertRaisesRegex(RuntimeError, "webhook failed"):
            watcher.process_new_pages(pages, state, timeout=20)

        self.assertEqual(saved_ids, [2])
        self.assertEqual(state["last_seen_id"], 2)

    def test_notification_target_detection(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(watcher.notification_target_is_configured())
        with patch.dict(
            os.environ,
            {"DISCORD_WEBHOOK_URL": "https://example.test"},
            clear=True,
        ):
            self.assertTrue(watcher.notification_target_is_configured())


if __name__ == "__main__":
    unittest.main()
