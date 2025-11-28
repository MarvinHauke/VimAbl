import pytest
from unittest.mock import MagicMock, patch
from src.server.services.project_service import ProjectService
from src.ast import ProjectNode

class MockServer:
    def __init__(self):
        self.current_ast = None
        self.current_file = None
        self.websocket_server = MagicMock()
        self.websocket_server.is_running.return_value = True
        self.websocket_server.broadcast_ast = AsyncMock()

    async def broadcast_diff(self, diff):
        pass

    # Mocking AsyncMock here for simplicity as server methods might be async or not
    # But project_service calls server methods? No, it sets server.current_ast
    # Let's check ProjectService

from unittest.mock import AsyncMock

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def service(server):
    return ProjectService(server)

def test_load_project_valid_file(service, server):
    """
    Test load_project with a valid file.
    """
    file_path = "test_project.als"
    
    # Mock parsing
    mock_tree = MagicMock()
    mock_root = MagicMock()
    mock_tree.getroot.return_value = mock_root
    mock_raw_ast = {"tracks": []}
    mock_project_node = ProjectNode()
    mock_project_node.id = "project-root"

    with patch("src.server.services.project_service.load_ableton_xml", return_value=mock_tree), \
         patch("src.server.services.project_service.build_ast", return_value=mock_raw_ast), \
         patch("src.server.services.project_service.ASTBuilder.build_node_tree", return_value=mock_project_node), \
         patch("src.server.services.project_service.hash_tree"):
        
        result = service.load_project(file_path, broadcast=False)

    assert result["status"] == "success"
    assert result["file"] == file_path
    assert server.current_ast == mock_project_node
    assert server.current_file == file_path

def test_load_project_invalid_file(service, server):
    """
    Test load_project raises exception for invalid files.
    """
    with patch("src.server.services.project_service.load_ableton_xml", side_effect=FileNotFoundError("File not found")):
        with pytest.raises(FileNotFoundError):
            service.load_project("non_existent.als")

    assert server.current_ast is None

def test_load_project_broadcast(service, server):
    """
    Test load_project triggers broadcast when enabled.
    """
    file_path = "test_project.als"
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = MagicMock()
    mock_raw_ast = {"tracks": []}
    mock_project_node = ProjectNode()
    
    with patch("src.server.services.project_service.load_ableton_xml", return_value=mock_tree), \
         patch("src.server.services.project_service.build_ast", return_value=mock_raw_ast), \
         patch("src.server.services.project_service.ASTBuilder.build_node_tree", return_value=mock_project_node), \
         patch("src.server.services.project_service.hash_tree"), \
         patch("asyncio.create_task") as mock_create_task:
        
        service.load_project(file_path, broadcast=True)
        
        mock_create_task.assert_called_once()

