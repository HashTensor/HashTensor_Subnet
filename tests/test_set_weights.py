import unittest
from unittest.mock import patch, MagicMock
from src.set_weights import set_weights, __spec_version__


class TestSetWeights(unittest.TestCase):
    @patch("src.set_weights.get_nodes_for_netuid_cached")
    @patch("src.set_weights.weights.set_node_weights")
    def test_set_weights_calls_set_node_weights(
        self, mock_set_node_weights, mock_get_nodes
    ):
        # Arrange
        substrate = MagicMock()
        keypair = MagicMock()
        keypair.ss58_address = "hotkey1"
        netuid = 42
        hotkey_to_rating = {"hotkey1": 1.0, "hotkey2": 0.5}
        nodes = [
            MagicMock(node_id=1, hotkey="hotkey1"),
            MagicMock(node_id=2, hotkey="hotkey2"),
        ]
        mock_get_nodes.return_value = nodes

        # Act
        set_weights(hotkey_to_rating, substrate, keypair, netuid)

        # Assert
        mock_set_node_weights.assert_called_once_with(
            substrate=substrate,
            keypair=keypair,
            node_ids=[1, 2],
            node_weights=[1.0, 0.5],
            netuid=netuid,
            validator_node_id=1,
            version_key=__spec_version__,
            wait_for_inclusion=True,
            wait_for_finalization=True,
        )

    @patch("src.set_weights.get_nodes_for_netuid_cached")
    @patch("src.set_weights.weights.set_node_weights")
    def test_set_weights_empty_ratings(
        self, mock_set_node_weights, mock_get_nodes
    ):
        substrate = MagicMock()
        keypair = MagicMock()
        netuid = 42
        hotkey_to_rating = {}
        set_weights(hotkey_to_rating, substrate, keypair, netuid)
        mock_set_node_weights.assert_not_called()

    @patch("src.set_weights.get_nodes_for_netuid_cached")
    def test_set_weights_validator_not_found(self, mock_get_nodes):
        substrate = MagicMock()
        keypair = MagicMock()
        keypair.ss58_address = "hotkey3"  # Not in nodes
        netuid = 42
        hotkey_to_rating = {"hotkey1": 1.0}
        nodes = [MagicMock(node_id=1, hotkey="hotkey1")]
        mock_get_nodes.return_value = nodes
        with self.assertRaises(ValueError):
            set_weights(hotkey_to_rating, substrate, keypair, netuid)


if __name__ == "__main__":
    unittest.main()
