
from extensions import register

register('console_script', 'foobar', 'foo:bar')

def bar():
    print 'Hey I am foo'


