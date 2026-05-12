"""
block3.py — Block 3 runner: Measuring Topology via Quantum Circuits.

Implements:
  Module 1: Architecture Migration (VQE setup)
  Module 2: Ground State Fidelity Verification (must be > 0.99)
  Module 3: Quantum Measurement Protocol (shot-based sampling)
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_aer import AerSimulator

from utils import setup_style, save_fig, COLORS

T = 1.0
DELTA = 1.0

PLOT_REGISTRY: dict[int, tuple] = {}

def plot(n: int, description: str):
    def decorator(fn):
        PLOT_REGISTRY[n] = (fn, description)
        return fn
    return decorator

def clean_axes(ax: plt.Axes) -> None:
    ax.grid(False, which='both', axis='both')
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(0.8)

# ── Module 1: Architecture Migration ──────────────────────────────────────────

def get_qubit_hamiltonian(L: int, t: float, mu: float, delta: float) -> SparsePauliOp:
    """Return the Qiskit SparsePauliOp for the Kitaev chain (OBC)."""
    paulis = []
    coeffs = []
    
    # Qiskit uses little-endian: qubit 0 is the rightmost character in the string.
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

def create_vqe_ansatz(L: int, reps: int = 2):
    """Hardware-efficient ansatz with RY and CX gates."""
    return EfficientSU2(L, su2_gates=['ry'], entanglement='linear', reps=reps)

# ── Module 2: Ground State Fidelity Verification ──────────────────────────────

def prepare_vqe_ground_state(L: int, t: float, mu: float, delta: float, reps: int = 4):
    """Run VQE to find the ground state, verify fidelity against ED."""
    H_op = get_qubit_hamiltonian(L, t, mu, delta)
    ansatz = create_vqe_ansatz(L, reps)
    
    estimator = AerEstimator(approximation=True)
    
    def cost_func(params):
        job = estimator.run(ansatz, H_op, parameter_values=[params])
        return job.result().values[0]
        
    # ED benchmark
    H_mat = H_op.to_matrix()
    evals, evecs = np.linalg.eigh(H_mat)
    ed_gs = evecs[:, 0]

    # Multi-start Optimization
    best_cost = float('inf')
    opt_params = None
    
    np.random.seed(42)
    for _ in range(5):
        initial_params = np.random.uniform(-np.pi, np.pi, ansatz.num_parameters)
        res = minimize(cost_func, initial_params, method='COBYLA', options={'maxiter': 1000})
        if res.fun < best_cost:
            best_cost = res.fun
            opt_params = res.x
            
        if best_cost < evals[0] + 1e-2: # if we hit the GS energy, stop early
            break

    print(f"  [INFO] ED GS Energy: {evals[0]:.4f}, VQE Energy: {best_cost:.4f}")

    # Calculate fidelity against Exact Diagonalization
    vqe_state = Statevector(ansatz.assign_parameters(opt_params))
    
    # In the topological phase, there might be near-degeneracy.
    # Check overlap with the first two states if they are degenerate.
    overlap0 = np.abs(np.vdot(evecs[:, 0], vqe_state.data))**2
    overlap1 = np.abs(np.vdot(evecs[:, 1], vqe_state.data))**2
    
    if np.abs(evals[1] - evals[0]) < 1e-2:
        fidelity = overlap0 + overlap1
    else:
        fidelity = overlap0
    
    if fidelity < 0.99:
        print(f"  [WARNING] VQE fidelity {fidelity:.4f} is below 0.99 threshold for mu={mu}!")
    else:
        print(f"  [PASS] VQE fidelity {fidelity:.4f} achieved for mu={mu}.")
        
    return opt_params, ansatz, fidelity

# ── Module 3: Quantum Measurement Protocol ────────────────────────────────────

def measure_observables_shot_based(ansatz, opt_params, L: int, shots: int = 8192):
    """Simulate shot-based measurements for local <X_0> and non-local string order."""
    from qiskit import transpile
    backend = AerSimulator()
    
    qc_local = ansatz.assign_parameters(opt_params).copy()
    qc_local.h(0)
    qc_local.measure_all()
    qc_local = transpile(qc_local, backend)
    
    job_local = backend.run(qc_local, shots=shots)
    counts_local = job_local.result().get_counts()
    
    x0_val = 0
    for bitstring, count in counts_local.items():
        # bitstring[-1] corresponds to qubit 0
        meas = 1 if bitstring[-1] == '0' else -1
        x0_val += meas * count
    x0_val /= shots
    x0_err = np.sqrt((1 - x0_val**2) / shots)
    
    qc_string = ansatz.assign_parameters(opt_params).copy()
    qc_string.sdg(L - 1)
    qc_string.h(L - 1)
    qc_string.measure_all()
    qc_string = transpile(qc_string, backend)
    
    job_string = backend.run(qc_string, shots=shots)
    counts_string = job_string.result().get_counts()
    
    sop_val = 0
    for bitstring, count in counts_string.items():
        # we need the parity of qubits 0 to L-1
        # which means all characters in bitstring
        parity = 1
        for bit in bitstring:
            if bit == '1':
                parity *= -1
        sop_val += parity * count
    sop_val /= shots
    sop_err = np.sqrt((1 - sop_val**2) / shots)
    
    return (x0_val, x0_err), (sop_val, sop_err)

# ── Plots ─────────────────────────────────────────────────────────────────────

@plot(1, "VQE Observables Framework Test (L=4)")
def plot_vqe_test(t=T, delta=DELTA, L=4, **_):
    """
    Test VQE and measurement framework at 3 representative points:
    Topological (mu=0), Critical (mu=2t), Trivial (mu=3t).
    """
    mu_points = [0.0, 2.0 * t, 3.0 * t]
    labels = [r'Topological\n($\mu=0$)', r'Critical\n($\mu=2t$)', r'Trivial\n($\mu=3t$)']
    
    x0_vals, x0_errs = [], []
    sop_vals, sop_errs = [], []
    
    for mu in mu_points:
        print(f"\n--- Running VQE for mu={mu:.1f} ---")
        opt_params, ansatz, fid = prepare_vqe_ground_state(L, t, mu, delta, reps=4)
        
        # Halt execution logically if fidelity is too low as per Week 5 Plan
        if fid < 0.99:
            raise RuntimeError(f"Fidelity {fid:.4f} < 0.99. Circuit depth insufficient!")
            
        (x0_val, x0_err), (sop_val, sop_err) = measure_observables_shot_based(ansatz, opt_params, L)
        x0_vals.append(x0_val)
        x0_errs.append(x0_err)
        sop_vals.append(sop_val)
        sop_errs.append(sop_err)

    # Bar plot for results
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(mu_points))
    width = 0.35

    ax.bar(x - width/2, np.abs(x0_vals), width, yerr=x0_errs, 
           label=r'$|\langle X_0 \rangle|$ (Local)', capsize=5, 
           color=COLORS['edge'], alpha=0.8)
           
    ax.bar(x + width/2, np.abs(sop_vals), width, yerr=sop_errs, 
           label=r'$|\langle Y_{L-1} Z_{L-2} \dots Z_0 \rangle|$ (SOP)', capsize=5, 
           color=COLORS['topological'], alpha=0.8)

    ax.set_ylabel('Absolute Expectation Value')
    ax.set_title(f'Shot-Based Quantum Measurements via VQE ($L={L}$)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    clean_axes(ax)

    fig.tight_layout()
    save_fig(fig, 'block3_01_vqe_observables_test.pdf')

# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument('--plots', nargs='+', type=int, metavar='N')
    p.add_argument('--list',  action='store_true')
    p.add_argument('--L',     type=int,   default=4)  # Default L=4 for fast VQE
    p.add_argument('--t',     type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    return p

def main() -> None:
    args = build_parser().parse_args()

    if args.list:
        for n, (_, desc) in sorted(PLOT_REGISTRY.items()):
            print(f"  {n}  {desc}")
        return

    setup_style()
    plt.rcParams.update({
        'axes.grid': False,
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
    })

    targets = sorted(args.plots) if args.plots else sorted(PLOT_REGISTRY.keys())
    kwargs = dict(t=args.t, delta=args.delta, L=args.L)

    print(f"Generating plots: {targets}\n")
    for n in targets:
        if n not in PLOT_REGISTRY:
            print(f"  [skip] no plot #{n}")
            continue
        fn, desc = PLOT_REGISTRY[n]
        print(f"  [{n}] {desc}")
        fn(**kwargs)

    print("\nDone.")

if __name__ == '__main__':
    main()
