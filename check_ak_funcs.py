import sys
import types

# Windows-specific asyncio fix for restricted environments (e.g. some sandboxes)
if sys.platform == 'win32':
    try:
        import _overlapped
    except OSError:
        mock_overlapped = types.ModuleType('_overlapped')
        mock_overlapped.Overlapped = type('Overlapped', (object,), {})
        mock_overlapped.CreateIoCompletionPort = lambda *args: 0
        mock_overlapped.GetQueuedCompletionStatus = lambda *args: 0
        mock_overlapped.PostQueuedCompletionStatus = lambda *args: 0
        mock_overlapped.INVALID_HANDLE_VALUE = -1
        mock_overlapped.NULL = 0
        sys.modules['_overlapped'] = mock_overlapped

import akshare as ak
import inspect

def find_news_functions():
    functions = []
    for name, obj in inspect.getmembers(ak):
        if inspect.isfunction(obj) and ('news' in name or 'telegraph' in name or 'sina' in name):
            functions.append(name)
    print("\n".join(functions))

if __name__ == "__main__":
    find_news_functions()
