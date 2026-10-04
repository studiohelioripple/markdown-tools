# Mathematical & Formula Conversion Showcase

This document demonstrates the full rendering fidelity of **LaTeX**, **TeX**, and **FMath-formula** expressions across inline and display formats.

---

## 1. Classical Physics & Relativity

- **Mass-Energy Equivalence**: The relationship between mass and energy is given by $E = mc^2$, where $c \approx 3 \times 10^8 \text{ m/s}$.
- **Lorentz Transformation Factor**:
  $$
  \gamma = \frac{1}{\sqrt{1 - \frac{v^2}{c^2}}}
  $$
- **Newton's Second Law**:
  ```latex
  \mathbf{F} = \frac{d\mathbf{p}}{dt} = m\mathbf{a}
  ```

---

## 2. Electromagnetism & Calculus

Maxwell's equations in differential form demonstrate vector calculus notation:

$$
\begin{align}
\nabla \cdot \mathbf{E} &= \frac{\rho}{\varepsilon_0} \\
\nabla \cdot \mathbf{B} &= 0 \\
\nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \\
\nabla \times \mathbf{B} &= \mu_0\left(\mathbf{J} + \varepsilon_0 \frac{\partial \mathbf{E}}{\partial t}\right)
\end{align}
$$

Gaussian integral over the whole real line:
\[
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
\]

---

## 3. Linear Algebra & Matrix Calculus

Matrix multiplication and determinants:

$$
\mathbf{A} = \begin{pmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn}
\end{pmatrix}, \quad
\det(\mathbf{A}) = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma) \prod_{i=1}^n a_{i,\sigma(i)}
$$

Piecewise function definition using `cases`:

$$
f(x) = \begin{cases}
0, & x < 0 \\
\frac{1}{2}, & x = 0 \\
1, & x > 0
\end{cases}
$$

---

## 4. FMath Formula & Custom HTML Extensions

Web and CMS math tags are natively parsed and styled:

- **Inline `<fmath>` tag**: <fmath>\lim_{x \to 0} \frac{\sin x}{x} = 1</fmath>
- **Inline `<fmath-formula>` tag**: <fmath-formula>\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}</fmath-formula>
- **Inline `<span class="fmath-formula">`**: <span class="fmath-formula">\oint_C \mathbf{F} \cdot d\mathbf{r} = \iint_S (\nabla \times \mathbf{F}) \cdot d\mathbf{S}</span>

Fenced FMath code block:

```fmath-formula
\zeta(s) = \sum_{n=1}^\infty \frac{1}{n^s} = \prod_{p \text{ prime}} \frac{1}{1 - p^{-s}}
```

Block `<div class="fmath-formula">`:

<div class="fmath-formula">
\mathcal{L}\{f(t)\} = F(s) = \int_0^\infty e^{-st} f(t) \, dt
</div>

---

## 5. Currency & Text Isolation

- Regular dollar amounts are never confused with equations: The total cost is **$149.99** with a discount of **$25.00**, leaving a net total of **$124.99**.
- While inline math like $\alpha + \beta = 180^\circ$ and $\theta \in [0, 2\pi)$ renders with mathematical precision.
