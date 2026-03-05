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
