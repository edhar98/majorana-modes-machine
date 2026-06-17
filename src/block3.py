import argparse
import numpy as np
import matplotlib.pyplot as plt

from qiskit_aer import AerSimulator

from block3_core import (
    T, DELTA,
    vqe_ansatz, prepare_vqe_ground_state,
    vqe_convergence, measure_local_x_shots, measure_edge_string_shots,
    sweep_observables, finite_size_sweep, noisy_value,
    vqe_sweep, depth_scan,
)
from bdg_bulk import critical_mu
from utils import setup_style, save_fig, COLORS, clean_axes

PLOT_REGISTRY: dict[int, tuple] = {}


def plot(n: int, description: str):
    def decorator(fn):
        PLOT_REGISTRY[n] = (fn, description)
        return fn
    return decorator


def _mu_label_color(mu, t):
    if abs(mu) < 1e-9:
        return r'topological $\mu=0$', COLORS['topological']
    if abs(abs(mu) - 2.0 * t) < 1e-9:
        return r'critical $\mu=2t$', COLORS['critical']
    return rf'trivial $\mu={mu / t:.0f}t$', COLORS['trivial']


@plot(1, "Week 5: VQE observables framework test (L=4)")
def plot_vqe_test(t=T, delta=DELTA, L=4, shots=8192, **_):
    mu_points = [0.0, 2.0 * t, 3.0 * t]
    labels = [r'Topological ($\mu=0$)', r'Critical ($\mu=2t$)', r'Trivial ($\mu=3t$)']
    backend = AerSimulator()

    local_vals, local_errs, edge_vals, edge_errs = [], [], [], []
    for mu in mu_points:
        print(f"\n--- Running VQE for mu={mu:.1f} ---")
        opt_params, ansatz, fid = prepare_vqe_ground_state(L, t, mu, delta, reps=4)
        if fid < 0.99:
            raise RuntimeError(f"Fidelity {fid:.4f} < 0.99. Circuit depth insufficient!")
        local_val = measure_local_x_shots(ansatz, opt_params, L, shots, backend, site=0)
        edge_val = measure_edge_string_shots(ansatz, opt_params, L, shots, backend)
        local_vals.append(local_val)
        local_errs.append(np.sqrt((1 - local_val ** 2) / shots))
        edge_vals.append(edge_val)
        edge_errs.append(np.sqrt((1 - edge_val ** 2) / shots))

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(mu_points))
    width = 0.35
    ax.bar(x - width / 2, np.abs(local_vals), width, yerr=local_errs,
           label=r'$|\langle X_0 \rangle|$ (local, parity odd)', capsize=5,
           color=COLORS['edge'], alpha=0.8)
    ax.bar(x + width / 2, np.abs(edge_vals), width, yerr=edge_errs,
           label=r'$|\langle X_0 Z_1 Z_2 X_3 \rangle|$ (edge string)', capsize=5,
           color=COLORS['topological'], alpha=0.8)
    ax.set_ylabel('Absolute Expectation Value')
    ax.set_title(f'Shot-Based Edge-String Measurements via VQE ($L={L}$)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.08)
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_01_vqe_observables_test.pdf')


@plot(2, "Week 5: slide figures at the mu=0 sweet spot")
def plot_week5_figures(L=4, t=T, delta=DELTA, reps=3, lam=0.1, seed=42, shots=8192, **_):
    history, exact_gs, fidelity, theta, ansatz = vqe_convergence(L, t, delta, reps=reps, lam=lam, seed=seed)
    print(f"  [week5] VQE converged: E={history[-1]:.4f} (exact {exact_gs:.4f}), fidelity={fidelity:.4f}")

    fig_ansatz = vqe_ansatz(L, reps=1).decompose().draw('mpl')
    save_fig(fig_ansatz, 'block3_week5_ansatz.pdf')

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(history, color=COLORS['topological'], lw=1.5, label=r'VQE energy $\langle H \rangle$')
    ax.axhline(exact_gs, color=COLORS['trivial'], ls='--', label=f'exact GS ({exact_gs:.4f})')
    ax.set_xlabel('Function evaluations')
    ax.set_ylabel(r'Energy expectation $\langle H \rangle$')
    ax.set_title(rf'Symmetry-broken VQE convergence ($L={L}$, $\mu=0$, $\mathcal{{F}}={fidelity:.4f}$)')
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week5_convergence.pdf')

    qc_local = vqe_ansatz(L, reps=1).copy()
    qc_local.h(0)
    qc_local.measure_all()
    save_fig(qc_local.decompose().draw('mpl'), 'block3_week5_meas_local.pdf')

    qc_sop = vqe_ansatz(L, reps=1).copy()
    qc_sop.sdg(L - 1)
    qc_sop.h(L - 1)
    qc_sop.measure_all()
    save_fig(qc_sop.decompose().draw('mpl'), 'block3_week5_meas_sop.pdf')

    qc_corr = vqe_ansatz(L, reps=1).copy()
    qc_corr.h(0)
    qc_corr.h(L - 1)
    qc_corr.measure_all()
    save_fig(qc_corr.decompose().draw('mpl'), 'block3_week5_meas_correlation.pdf')

    backend = AerSimulator()
    y0 = measure_local_y_shots(ansatz, theta, L, shots, backend, site=0)
    string = measure_edge_string_shots(ansatz, theta, L, shots, backend)
    y0_err = np.sqrt(max(1 - y0 ** 2, 0.0) / shots)
    string_err = np.sqrt(max(1 - string ** 2, 0.0) / shots)

    fig, ax = plt.subplots(figsize=(7, 5))
    labels = [r'Local $\langle Y_0 \rangle$', r'String $\langle X_0 Z\cdots Z X_{L-1} \rangle$']
    vals = [abs(y0), abs(string)]
    errs = [y0_err, string_err]
    bars = ax.bar(labels, vals, yerr=errs, capsize=8, alpha=0.85,
                  color=[COLORS['bulk'], COLORS['topological']],
                  error_kw=dict(lw=1.5, capthick=1.5, ecolor='black'))
    ax.axhline(1.0, color='black', ls='--', lw=1.2, label='topological limit')
    for bar, v, e in zip(bars, vals, errs):
        ax.text(bar.get_x() + bar.get_width() / 2, v + e + 0.03, f'{v:.4f}',
                ha='center', va='bottom', fontsize=10)
    ax.set_ylim(0, 1.25)
    ax.set_ylabel(r'$|\langle \hat{O} \rangle|$')
    ax.set_title(rf'Majorana signatures at $\mu=0$ ($L={L}$)')
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week5_correlation.pdf')


@plot(3, "Week 6: edge-string phase sweep")
def plot_week6_phase_sweep(L=4, t=T, delta=DELTA, shots=4096, points=81, **_):
    data = sweep_observables(L=L, t=t, delta=delta, shots=shots, points=points)
    mu_c1, mu_c2 = critical_mu(t)
    x = data['mu'] / t

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'],
               label=r'topological $|\mu|<2t$')
    ax.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax.plot(x, np.abs(data['string_exact']), color=COLORS['topological'], lw=2.6,
            label=r'exact $|\langle O_{\mathrm{edge}} \rangle|$')
    ax.scatter(x[::4], np.abs(data['string_shot'][::4]), color=COLORS['topological'], s=22,
               zorder=3, label=rf'{shots} shot estimator')
    ax.plot(x, np.abs(data['local_exact']), color=COLORS['bulk'], lw=1.8, ls=':',
            label=r'local $|\langle Z_0 \rangle|$')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel('Expectation value')
    ax.set_title('Non-local diagnostic of the Kitaev phase transition')
    ax.set_ylim(-0.05, 1.08)
    ax.legend(fontsize=9, loc='upper center')
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week6_phase_sweep.pdf')


@plot(4, "Week 6: finite-size scaling of the edge string")
def plot_finite_size(t=T, delta=DELTA, shots=4096, **_):
    L_list = (4, 6, 8)
    data = finite_size_sweep(L_list, t, delta, shots)

    fig, ax = plt.subplots(figsize=(7.5, 5))
    mu_c1, mu_c2 = critical_mu(t)
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    for L in L_list:
        x = data[L]['mu'] / t
        ax.plot(x, np.abs(data[L]['string_exact']), lw=2, label=f'L={L}')
    ax.set_title('Finite-size effects on topological correlator')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}} \rangle|$')
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week6_finite_size.pdf')


@plot(5, "Week 6: local vs non-local observables")
def plot_local_vs_nonlocal(L=4, t=T, delta=DELTA, shots=4096, points=81, **_):
    data = sweep_observables(L=L, t=t, delta=delta, shots=shots, points=points)
    x = data['mu'] / t

    fig, ax = plt.subplots(figsize=(7.5, 5))
    mu_c1, mu_c2 = critical_mu(t)
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax.plot(x, np.abs(data['string_exact']), lw=2.5, label='non-local string')
    ax.plot(x, np.abs(data['local_exact']), lw=2.0, ls='--', label='local Z observable')
    ax.set_title('Local vs non-local observables')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel('Expectation value')
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week6_local_vs_nonlocal.pdf')


@plot(6, "Week 6: classical noise robustness of the diagnostic")
def plot_noise_robustness(L=4, t=T, delta=DELTA, shots=4096, points=81,
                          noise_levels=(0.0, 0.1, 0.2), **_):
    base = sweep_observables(L=L, t=t, delta=delta, shots=shots, points=points)
    x = base['mu'] / t
    rng = np.random.default_rng(123)

    fig, ax = plt.subplots(figsize=(7.5, 5))
    mu_c1, mu_c2 = critical_mu(t)
    ax.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax.plot(x, np.abs(base['string_exact']), lw=2.5, label='ideal')
    for noise in noise_levels[1:]:
        noisy_curve = [noisy_value(v, noise, rng) for v in base['string_exact']]
        ax.plot(x, np.abs(noisy_curve), lw=1.5, label=f'noise={noise}')
    ax.set_title('Noise robustness of topological diagnostic')
    ax.set_xlabel(r'$\mu/t$')
    ax.set_ylabel(r'$|\langle O_{\mathrm{edge}} \rangle|$')
    ax.legend()
    clean_axes(ax)
    fig.tight_layout()
    save_fig(fig, 'block3_week6_noise.pdf')


@plot(7, "Week 7: parity-constrained VQE mu-sweep")
def plot_vqe_sweep(L=4, t=T, delta=DELTA, points=81, shots=4096, reps=3, lam=3.0,
                   seed=7, maxiter=500, restarts=4, **_):
    mu_values, rows = vqe_sweep(L, t, delta, points, shots, reps, lam, seed, maxiter, restarts)
    x = mu_values / t
    s_ed = np.abs(np.array([r['string_ed'] for r in rows]))
    s_vqe = np.abs(np.array([r['string'] for r in rows]))
    s_shot = np.abs(np.array([r['string_shot'] for r in rows]))
    de = np.abs(np.array([r['energy'] - r['energy_ed'] for r in rows]))
    infid = np.abs(np.array([1.0 - r['fidelity'] for r in rows]))
    dp = np.abs(np.array([1.0 - r['parity'] for r in rows]))
    recovered = np.array([r['recovered'] for r in rows])

    mu_c1, mu_c2 = critical_mu(t)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.8, 7.2), sharex=True)

    ax1.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'],
                label=r'topological $|\mu|<2t$')
    ax1.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax1.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax1.plot(x, s_ed, color='black', lw=2.2, label=r'ED $|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.plot(x, s_vqe, color=COLORS['topological'], lw=0, marker='o', ms=4, label='VQE (ideal)')
    ax1.scatter(x[::2], s_shot[::2], color=COLORS['edge'], s=20, zorder=3,
                label=rf'VQE ({shots} shots)')
    ax1.set_ylabel(r'$|\langle O_{\mathrm{edge}}\rangle|$')
    ax1.set_title(f'Week 7: VQE-prepared edge-string sweep (L={L}, t=1, Delta=1)')
    ax1.set_ylim(-0.05, 1.08)
    ax1.legend(fontsize=9, loc='upper center', ncol=2)
    clean_axes(ax1)

    ax2.axvspan(mu_c1 / t, mu_c2 / t, alpha=0.10, color=COLORS['topological'])
    ax2.axvline(mu_c1 / t, color='gray', ls='--', lw=1)
    ax2.axvline(mu_c2 / t, color='gray', ls='--', lw=1)
    ax2.semilogy(x, de + 1e-16, color=COLORS['trivial'], lw=1.8,
                 label=r'$|E_{\mathrm{VQE}}-E_{\mathrm{ED}}|$')
    ax2.semilogy(x, infid + 1e-16, color=COLORS['critical'], lw=1.8, label=r'$1-\mathcal{F}$')
    ax2.semilogy(x, dp + 1e-16, color=COLORS['bulk'], lw=1.8, ls='--',
                 label=r'$|1-\langle P\rangle|$')
    if recovered.any():
        ax2.scatter(x[recovered], (de + 1e-16)[recovered], color='black', marker='x',
                    s=40, zorder=4, label='restart used')
    ax2.set_xlabel(r'$\mu/t$')
    ax2.set_ylabel('validation error')
    ax2.legend(fontsize=8, loc='lower center', ncol=2)
    clean_axes(ax2)

    fig.tight_layout()
    save_fig(fig, 'block3_week7_vqe_sweep.pdf')


@plot(8, "Week 7: ansatz-depth fidelity diagnostic")
def plot_depth_fidelity(L=4, t=T, delta=DELTA, lam=3.0, seed=7, maxiter=500, starts=6,
                        reps_list=(1, 2, 3, 4, 5), mu_points=(0.0, 2.0, 3.0), **_):
    mu_abs = [m * t for m in mu_points]
    reps_list = list(reps_list)
    results = depth_scan(L, t, delta, mu_abs, reps_list, lam, seed, maxiter, starts)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for mu, row in results.items():
        reps = [r['reps'] for r in row]
        infid = [max(1.0 - r['fidelity'], 1e-16) for r in row]
        de = [max(abs(r['energy'] - r['energy_ed']), 1e-16) for r in row]
        label, color = _mu_label_color(mu, t)
        ax1.semilogy(reps, infid, marker='o', color=color, lw=2, label=label)
        ax2.semilogy(reps, de, marker='o', color=color, lw=2, label=label)

    ax1.axhline(1e-2, color='gray', ls=':', lw=1.2, label=r'$1-\mathcal{F}=10^{-2}$')
    ax1.set_xlabel('ansatz reps')
    ax1.set_ylabel(r'$1-\mathcal{F}$')
    ax1.set_title('Subspace infidelity vs depth')
    ax1.set_xticks(reps_list)
    ax1.legend(fontsize=8)
    clean_axes(ax1)

    ax2.set_xlabel('ansatz reps')
    ax2.set_ylabel(r'$|E_{\mathrm{VQE}}-E_{\mathrm{ED}}|$')
    ax2.set_title('Energy error vs depth')
    ax2.set_xticks(reps_list)
    ax2.legend(fontsize=8)
    clean_axes(ax2)

    fig.suptitle(rf'Week 7: ansatz-depth diagnostic ($L={L}$, $t=\Delta=1$)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, 'block3_week7_depth_fidelity.pdf')


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Block 3 runner: Weeks 5-7 (measuring topology).')
    p.add_argument('--plots', nargs='+', type=int, metavar='N')
    p.add_argument('--list', action='store_true')
    p.add_argument('--L', type=int, default=4)
    p.add_argument('--t', type=float, default=T)
    p.add_argument('--delta', type=float, default=DELTA)
    p.add_argument('--points', type=int, default=81)
    p.add_argument('--shots', type=int, default=4096)
    p.add_argument('--reps', type=int, default=3)
    p.add_argument('--lam', type=float, default=3.0)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--maxiter', type=int, default=500)
    p.add_argument('--restarts', type=int, default=4)
    p.add_argument('--starts', type=int, default=6)
    p.add_argument('--reps-list', nargs='+', type=int, default=[1, 2, 3, 4, 5])
    p.add_argument('--mu-points', nargs='+', type=float, default=[0.0, 2.0, 3.0])
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
    kwargs = dict(
        t=args.t, delta=args.delta, L=args.L, points=args.points, shots=args.shots,
        reps=args.reps, lam=args.lam, seed=args.seed, maxiter=args.maxiter,
        restarts=args.restarts, starts=args.starts, reps_list=args.reps_list,
        mu_points=args.mu_points,
    )

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
