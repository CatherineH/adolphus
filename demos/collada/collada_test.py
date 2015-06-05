from adolphus.interface import Experiment
import os
foldername = os.path.dirname(os.path.realpath(__file__))
ex = Experiment(zoom=False)
ex.execute('loadmodel %s' % foldername+'/scene.yaml')
ex.execute('loadconfig %s' % '')

ex.start()
