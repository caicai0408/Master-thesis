import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()


np.random.seed(0)
tf.set_random_seed(0)

NX = 64 #number of sites 64
NP = 64 #number of particle 64
NSAMPLE = 1024  #number of sample
U = 1   # tunneling coefficient
J = -1  # on-site interaction energy

# tensorflow model
class Network:
    hidden_units = 256

    def __init__(self):
        self.prepare_model()
        self.prepare_session()

    def prepare_model(self):
        # hidden_units
        n1 = Network.hidden_units
        # input unit
        x = tf.placeholder(tf.float32, [None, NX])
        # weight
        w1 = tf.Variable(tf.truncated_normal([NX, n1]) * 0.1)
        # bias
        b1 = tf.Variable(tf.zeros([n1]))
        # hidden unit+activation function
        # hidden = tf.nn.tanh(tf.matmul(x, w1) + b1)
        hidden = tf.nn.relu(tf.matmul(x, w1) + b1)
        # initial weight
        w0 = tf.Variable(tf.truncated_normal([n1, 1]) * 0.1)
        output = tf.matmul(hidden, w0)

        # ground state energy
        eloc = tf.placeholder(tf.float32, [None, 1])
        # the reduce state energy
        ene = tf.reduce_mean(eloc)
        # loss function
        loss = tf.reduce_sum(output * (eloc - ene))
        # optimization
        train_step = tf.train.AdamOptimizer().minimize(loss)

        self.x, self.output = x, output
        self.eloc, self.ene, self.loss = eloc, ene, loss
        self.train_step = train_step

    def prepare_session(self):
        sess = tf.Session()
        sess.run(tf.global_variables_initializer())
        self.sess = sess

    def forward(self, num):
        return self.sess.run(self.output, feed_dict={self.x: num}).ravel()

    def optimize(self, state, eloc):
        eloc = eloc.reshape(NSAMPLE, 1)
        self.sess.run(self.train_step,
                      feed_dict={self.x: state.num, self.eloc:  eloc})



class SampledState:
    thermalization_n = 1024

    def __init__(self, net):
        self.num = np.zeros(NSAMPLE * NX)
        self.num = self.num.reshape(NSAMPLE, NX)
        for i in range(NSAMPLE):
            for j in range(NP):
                self.num[i][j % NX] += 1
        self.lnpsi = net.forward(self.num)

    def try_flip(self, net):
        num_tmp = np.copy(self.num)
        for i in range(NSAMPLE):
            p0 = np.random.randint(NX)
            p1 = np.random.randint(NX)
            if num_tmp[i][p0] > 0 and p0 != p1:
                num_tmp[i][p0] -= 1
                num_tmp[i][p1] += 1
        lnpsi_tmp = net.forward(num_tmp)
        r = np.random.rand(NSAMPLE)
        isflip = r < np.exp(2 * (lnpsi_tmp - self.lnpsi))
        for i in range(NSAMPLE):
            if isflip[i]:
                self.num[i] = num_tmp[i]
                self.lnpsi[i] = lnpsi_tmp[i]

    def thermalize(self, net):
        for i in range(SampledState.thermalization_n):
            self.try_flip(net)

#-----------------------------------

def LocalEnergy(net, state):
    st = np.zeros((NSAMPLE, NX, 2, NX))
    st += state.num.reshape(NSAMPLE, 1, 1, NX)
    for b in range(NSAMPLE):
        for j in range(NX):
            if state.num[b][j] > 0:
                st[b][j][0][j] -= 1
                st[b][j][0][(j+1) % NX] += 1
                st[b][j][1][j] -= 1
                st[b][j][1][(j-1+NX)%NX] += 1
    st = st.reshape(NSAMPLE * NX * 2, NX)
    lnpsi2 = net.forward(st).reshape(NSAMPLE, NX, 2)
    eloc = np.zeros(NSAMPLE)
    for b in range(NSAMPLE):
        onsite = hopping = 0
        for j in range(NX):
            if state.num[b][j] > 0:
                onsite += 0.5 * U * state.num[b][j] * (state.num[b][j] - 1)
                hopping += J * np.sqrt(state.num[b][j]
                                       * (state.num[b][(j+1)%NX] + 1)) \
                    * np.exp(lnpsi2[b][j][0] - state.lnpsi[b])
                hopping += J * np.sqrt(state.num[b][j]
                                       * (state.num[b][(j-1+NX)%NX] + 1)) \
                    * np.exp(lnpsi2[b][j][1] - state.lnpsi[b])
        eloc[b] = onsite + hopping
    return eloc
# -------------- main -----------------

net = Network()

state = SampledState(net)
state.thermalize(net)

counter = 0


while counter <= 1000:
    # try_flip state
    for i in range(32):
        state.try_flip(net)
    # got LocalEnergy
    eloc = LocalEnergy(net, state)
    # optimize LocalEnergy
    net.optimize(state, eloc)
    # Output data every 10 times
    if counter % 2 == 0:
        with open(r'/home/huang/pyvenv/Program/NQS/ouput/relu_1.txt', 'a+') as tf:
            tf.write(str(counter))
            tf.write(' ')
            tf.write(str(eloc.mean()))
            tf.write('\n')
            tf.close()
        # print(counter, eloc.mean(), flush=True)
    counter += 1




