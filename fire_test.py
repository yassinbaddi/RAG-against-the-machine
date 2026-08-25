import fire

def test(name, count=1, enabled=True):
    print(name, count, enabled)

if __name__ == "__main__":
    fire.Fire(test)
