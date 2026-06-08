from dotenv import find_dotenv, load_dotenv
import os
p = find_dotenv()
print('FOUND:', repr(p))
if p:
    try:
        with open(p, 'r') as f:
            print('--- FILE CONTENTS ---')
            print(f.read())
    except Exception as e:
        print('read error', e)
load_dotenv(override=True)
print('GROQ:', os.getenv('GROQ_API_KEY'))
print('CWD:', os.getcwd())
print('PWD listing:')
print('\n'.join(os.listdir('.')))
