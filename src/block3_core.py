import numpy as np
from scipy.optimize import minimize
from qiskit import transpile
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_aer import AerSimulator

T = 1.0
DELTA = 1.0
TOLS = (5e-2, 1e-2, 0.99)


def qubit_hamiltonian(L, t, mu, delta):
    paulis, coeffs = [], []
    for j in range(L):
        s = ['I'] * L
        s[L - 1 - j] = 'Z'
        paulis.append("".join(s))
        coeffs.append(-mu / 2)
    for j in range(L - 1):
        s = ['I'] * L
        s[L - 1 - j] = 'X'
        s[L - 1 - (j + 1)] = 'X'
        paulis.append("".join(s))
        coeffs.append((t - delta) / 2)
        s = ['I'] * L
        s[L - 1 - j] = 'Y'
        s[L - 1 - (j + 1)] = 'Y'
        paulis.append("".join(s))
        coeffs.append((t + delta) / 2)
    return SparsePauliOp(paulis, coeffs)


def vqe_ansatz(L, reps=2):
    return EfficientSU2(L, su2_gates=['ry'], entanglement='linear', reps=reps)


def edge_string(L):
    label = ['Z'] * L
    label[L - 1] = 'X'
    label[0] = 'X'
    return SparsePauliOp(["".join(label)], [1.0])


def local_z(L, site=0):
    label = ['I'] * L
    label[L - 1 - site] = 'Z'
    return SparsePauliOp(["".join(label)], [1.0])


def parity(L):
    return SparsePauliOp(["Z" * L], [1.0])


def expval(psi, M):
    return float(np.real(np.vdot(psi, M @ psi)))


def state_vector(ansatz, theta):
    return Statevector(ansatz.assign_parameters(theta)).data


def ed_sectors(H_mat, P_mat):
    evals, evecs = np.linalg.eigh(H_mat)
    parities = np.real(np.einsum('ij,ij->j', evecs.conj(), P_mat @ evecs))
    even = parities > 0
    ie = np.where(even)[0][np.argmin(evals[even])]
    io = np.where(~even)[0][np.argmin(evals[~even])]
    return float(evals[ie]), evecs[:, ie], float(evals[io]), evecs[:, io]


def ed_even_ground_state(H_mat, P_mat):
    e, v, _, _ = ed_sectors(H_mat, P_mat)
    return e, v


def shot_estimate(value, shots, rng):
    p_plus = np.clip((1.0 + value) / 2.0, 0.0, 1.0)
    plus = rng.binomial(shots, p_plus)
    return (2 * plus - shots) / shots


def noisy_value(value, noise_strength, rng):
    return (1 - noise_strength) * value + noise_strength * rng.normal(0, 1)


def sweep_observables(L=4, t=T, delta=DELTA, shots=4096, seed=7, span=3.5, points=81):
    mu_values = np.linspace(-span * t, span * t, points)
    O = edge_string(L).to_matrix()
    Zop = local_z(L, 0).to_matrix()
    P = parity(L).to_matrix()
    rng = np.random.default_rng(seed)

    string_exact, string_shot, local_exact, parity_gaps = [], [], [], []
    for mu in mu_values:
        H = qubit_hamiltonian(L, t, mu, delta).to_matrix()
        ee, psi, eo, _ = ed_sectors(H, P)
        s = expval(psi, O)
        z = expval(psi, Zop)
        string_exact.append(s)
        string_shot.append(shot_estimate(s, shots, rng))
        local_exact.append(z)
        parity_gaps.append(abs(ee - eo))

    return {
        'mu': mu_values,
        'string_exact': np.array(string_exact),
        'string_shot': np.array(string_shot),
        'local_exact': np.array(local_exact),
        'parity_gap': np.array(parity_gaps),
    }


def finite_size_sweep(L_list=(4, 6, 8), t=T, delta=DELTA, shots=4096):
    return {L: sweep_observables(L=L, t=t, delta=delta, shots=shots) for L in L_list}


def prepare_vqe_ground_state(L, t, mu, delta, reps=4):
    H_op = qubit_hamiltonian(L, t, mu, delta)
    ansatz = vqe_ansatz(L, reps)
    estimator = AerEstimator(approximation=True)

    def cost_func(params):
        job = estimator.run(ansatz, H_op, parameter_values=[params])
        return job.result().values[0]

    H_mat = H_op.to_matrix()
    evals, evecs = np.linalg.eigh(H_mat)

    best_cost = float('inf')
    opt_params = None
    np.random.seed(42)
    for _ in range(5):
        initial_params = np.random.uniform(-np.pi, np.pi, ansatz.num_parameters)
        res = minimize(cost_func, initial_params, method='COBYLA', options={'maxiter': 1000})
        if res.fun < best_cost:
            best_cost = res.fun
            opt_params = res.x
        if best_cost < evals[0] + 1e-2:
            break

    print(f"  [INFO] ED GS Energy: {evals[0]:.4f}, VQE Energy: {best_cost:.4f}")

    vqe_state = Statevector(ansatz.assign_parameters(opt_params))
    overlap0 = np.abs(np.vdot(evecs[:, 0], vqe_state.data)) ** 2
    overlap1 = np.abs(np.vdot(evecs[:, 1], vqe_state.data)) ** 2
    if np.abs(evals[1] - evals[0]) < 1e-2:
        fidelity = overlap0 + overlap1
    else:
        fidelity = overlap0

    if fidelity < 0.99:
        print(f"  [WARNING] VQE fidelity {fidelity:.4f} is below 0.99 threshold for mu={mu}!")
    else:
        print(f"  [PASS] VQE fidelity {fidelity:.4f} achieved for mu={mu}.")

    return opt_params, ansatz, fidelity


def vqe_convergence(L, t, delta, reps=3, lam=0.1, seed=42, maxiter=10000):
    H_mat = qubit_hamiltonian(L, t, 0.0, delta).to_matrix()
    P_mat = parity(L).to_matrix()
    ansatz = vqe_ansatz(L, reps)
    evals, evecs = np.linalg.eigh(H_mat)
    exact_gs = float(evals[0])
    degenerate = np.where(evals < exact_gs + 1e-6)[0]

    history = []

    def cost(params):
        psi = state_vector(ansatz, params)
        e = expval(psi, H_mat)
        p = expval(psi, P_mat)
        history.append(e)
        return e - lam * p

    np.random.seed(seed)
    x0 = np.random.uniform(-np.pi, np.pi, ansatz.num_parameters)
    res = minimize(cost, x0, method='L-BFGS-B', options={'maxiter': maxiter, 'ftol': 1e-6})

    psi = state_vector(ansatz, res.x)
    fidelity = float(sum(np.abs(np.vdot(evecs[:, i], psi)) ** 2 for i in degenerate))
    return np.array(history), exact_gs, fidelity, res.x, ansatz


def measure_local_y_shots(ansatz, theta, L, shots, backend, site=0):
    qc = ansatz.assign_parameters(theta).copy()
    qc.sdg(site)
    qc.h(site)
    qc.measure_all()
    qc = transpile(qc, backend)
    counts = backend.run(qc, shots=shots).result().get_counts()
    val = 0
    for bitstring, count in counts.items():
        bit = bitstring.replace(' ', '')[L - 1 - site]
        val += (-1 if bit == '1' else 1) * count
    return val / shots


def measure_local_x_shots(ansatz, theta, L, shots, backend, site=0):
    qc = ansatz.assign_parameters(theta).copy()
    qc.h(site)
    qc.measure_all()
    qc = transpile(qc, backend)
    counts = backend.run(qc, shots=shots).result().get_counts()
    val = 0
    for bitstring, count in counts.items():
        bit = bitstring.replace(' ', '')[L - 1 - site]
        val += (-1 if bit == '1' else 1) * count
    return val / shots


def vqe_cost(theta, ansatz, H_mat, P_mat, lam):
    psi = state_vector(ansatz, theta)
    return expval(psi, H_mat) + lam * (1.0 - expval(psi, P_mat)) ** 2


def evaluate_state(theta, ansatz, H_mat, P_mat, O_mat, e_ed, psi_ed, tols=TOLS):
    tol_e, tol_p, tol_f = tols
    psi = state_vector(ansatz, theta)
    e = expval(psi, H_mat)
    p = expval(psi, P_mat)
    s = expval(psi, O_mat)
    fid = float(np.abs(np.vdot(psi_ed, psi)) ** 2)
    passed = (abs(e - e_ed) <= tol_e) and (abs(1.0 - p) <= tol_p) and (fid >= tol_f)
    return {'theta': theta, 'energy': e, 'parity': p, 'string': s,
            'fidelity': fid, 'passed': passed}


def measure_edge_string_shots(ansatz, theta, L, shots, backend):
    qc = ansatz.assign_parameters(theta).copy()
    qc.h(0)
    qc.h(L - 1)
    qc.measure_all()
    qc = transpile(qc, backend)
    counts = backend.run(qc, shots=shots).result().get_counts()
    val = 0
    for bitstring, count in counts.items():
        parity_sign = 1
        for bit in bitstring.replace(' ', ''):
            if bit == '1':
                parity_sign *= -1
        val += parity_sign * count
    return val / shots


def solve_point(mu, L, t, delta, ansatz, lam, theta0, rng, maxiter, restarts, tols=TOLS):
    H_mat = qubit_hamiltonian(L, t, mu, delta).to_matrix()
    P_mat = parity(L).to_matrix()
    O_mat = edge_string(L).to_matrix()
    e_ed, psi_ed = ed_even_ground_state(H_mat, P_mat)
    s_ed = expval(psi_ed, O_mat)

    args = (ansatz, H_mat, P_mat, lam)
    res = minimize(vqe_cost, theta0, args=args, method='COBYLA', options={'maxiter': maxiter})
    nfev = res.nfev
    candidates = [evaluate_state(res.x, ansatz, H_mat, P_mat, O_mat, e_ed, psi_ed, tols)]

    recovered = False
    if not candidates[0]['passed']:
        recovered = True
        for _ in range(restarts):
            theta_rand = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)
            r = minimize(vqe_cost, theta_rand, args=args, method='COBYLA', options={'maxiter': maxiter})
            nfev += r.nfev
            candidates.append(evaluate_state(r.x, ansatz, H_mat, P_mat, O_mat, e_ed, psi_ed, tols))

    best = max(candidates, key=lambda c: c['fidelity'])
    best.update({'mu': mu, 'energy_ed': e_ed, 'string_ed': s_ed, 'nfev': nfev,
                 'restarts': len(candidates) - 1, 'recovered': recovered})
    return best


def vqe_sweep(L, t, delta, points, shots, reps, lam, seed, maxiter, restarts, span=3.5):
    mu_values = np.linspace(-span * t, span * t, points)
    ansatz = vqe_ansatz(L, reps)
    rng = np.random.default_rng(seed)
    backend = AerSimulator()
    theta = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)

    rows = []
    for mu in mu_values:
        rec = solve_point(mu, L, t, delta, ansatz, lam, theta, rng, maxiter, restarts)
        theta = rec['theta']
        rec['string_shot'] = measure_edge_string_shots(ansatz, theta, L, shots, backend)
        rows.append(rec)
        print(f"  mu={rec['mu']:+.3f}  dE={abs(rec['energy'] - rec['energy_ed']):.2e}  "
              f"P={rec['parity']:+.4f}  fid={rec['fidelity']:.4f}  "
              f"|O|ed={abs(rec['string_ed']):.3f}  |O|vqe={abs(rec['string']):.3f}  "
              f"shot={abs(rec['string_shot']):.3f}  restarts={rec['restarts']}")

    failed = sum(1 for r in rows if not r['passed'])
    recovered = sum(1 for r in rows if r['recovered'])
    print(f"\n  points={len(rows)}  recovered={recovered}  failed_after_recovery={failed}  "
          f"total_evals={sum(r['nfev'] for r in rows)}")
    return mu_values, rows


def best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts, tols=TOLS):
    H_mat = qubit_hamiltonian(L, t, mu, delta).to_matrix()
    P_mat = parity(L).to_matrix()
    O_mat = edge_string(L).to_matrix()
    e_ed, psi_ed = ed_even_ground_state(H_mat, P_mat)

    args = (ansatz, H_mat, P_mat, lam)
    candidates = []
    for _ in range(n_starts):
        theta0 = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)
        r = minimize(vqe_cost, theta0, args=args, method='COBYLA', options={'maxiter': maxiter})
        candidates.append(evaluate_state(r.x, ansatz, H_mat, P_mat, O_mat, e_ed, psi_ed, tols))
    best = max(candidates, key=lambda c: c['fidelity'])
    best.update({'mu': mu, 'energy_ed': e_ed})
    return best


def depth_scan(L, t, delta, mu_points, reps_list, lam, seed, maxiter, n_starts):
    rng = np.random.default_rng(seed)
    results = {}
    for mu in mu_points:
        row = []
        for reps in reps_list:
            ansatz = vqe_ansatz(L, reps)
            rec = best_state(mu, L, t, delta, ansatz, lam, rng, maxiter, n_starts)
            rec['reps'] = reps
            rec['n_params'] = ansatz.num_parameters
            row.append(rec)
            print(f"  mu={mu:+.3f}  reps={reps}  params={rec['n_params']:>2}  "
                  f"dE={abs(rec['energy'] - rec['energy_ed']):.2e}  "
                  f"fid={rec['fidelity']:.4f}  pass={rec['passed']}")
        results[mu] = row
    return results
