from inspect import isawaitable
import time
import asyncio
import nest_asyncio
import random
from async_generator import yield_
import async_generator

nest_asyncio.apply()


async def afunc():
    await asyncio.sleep(0.5)
    print('afunc runed')
    await asyncio.sleep(0.5)
    return 'a'


async def bfunc():
    await afunc()
    await asyncio.sleep(0.5)
    print('bfunc runed')
    await asyncio.sleep(0.5)
    return 'b'


def test():
    try:
        loop = asyncio.get_running_loop()
    except:
        loop = asyncio.get_event_loop()

    print(loop.run_until_complete(afunc()))
    print(loop.run_until_complete(bfunc()))


async def cfunc():
    test()
    print('bfunc runed')
    return 'c'


def test1():
    try:
        loop = asyncio.get_running_loop()
    except:
        loop = asyncio.get_event_loop()

    print(loop.run_until_complete(cfunc()))


# 同步函数转换为异步IO处理
@asyncio.coroutine
def sync_fun(p):
    print('sync_fun run begin: %s' % p)
    # 真正耗费IO的部分这样处理
    io_resp = yield from asyncio.sleep(3 * random.random())
    print('fun 1 run end: %s' % str(io_resp))
    return 'p'


def test2():
    try:
        loop = asyncio.get_running_loop()
    except:
        loop = asyncio.get_event_loop()

    for i in range(10):
        loop.run_until_complete(sync_fun(str(i)))


async def iter(a):
    print('begin')
    b = [10, 11]
    try:
        if a:
            return 'test'
        else:
            @async_generator.async_generator
            async def test(c):
                for i in range(10):
                    await yield_(c)

            return test(b)
    finally:
        b.extend([12, 13])
        print('end')


async def deal_iter(a):
    iter_obj = await iter(a)
    await asyncio.sleep(3)
    if type(iter_obj) != async_generator._impl.AsyncGenerator:
        print(iter_obj)
    else:
        async for _item in iter_obj:
            print('iter: %s' % str(_item))


def test3():
    try:
        loop = asyncio.get_running_loop()
    except:
        loop = asyncio.get_event_loop()

    loop.run_until_complete(deal_iter(True))
    loop.run_until_complete(deal_iter(False))


async def iter_new():
    for i in range(10):
        yield i


def iter_sync():
    for i in range(100, 110):
        yield i


async def deal_iter_new():
    iter_obj = iter_new()
    iter_sync_obj = iter_sync()
    async for _item in iter_obj:
        print('iter: %s' % str(_item))

    for _item in iter_sync_obj:
        print('iter_sync: %s' % str(_item))


def test4():
    try:
        loop = asyncio.get_running_loop()
    except:
        loop = asyncio.get_event_loop()

    loop.run_until_complete(deal_iter_new())


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # test()
    # test1()
    # test2()
    # test3()
    # test4()
    import re
    print(re.sub(r"\'", "''", "abc'', d', e', "))
