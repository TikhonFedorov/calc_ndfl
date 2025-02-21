from flask import Flask, render_template, request

app = Flask(__name__)

# Месячные пороги для расчёта НДФЛ (на основе годовых значений, делённых на 12)
THRESHOLD1 = 2_400_000 / 12       # 200,000 руб.
THRESHOLD2 = 5_000_000 / 12       # ≈416,667 руб.
THRESHOLD3 = 20_000_000 / 12      # ≈1,666,667 руб.
THRESHOLD4 = 50_000_000 / 12      # ≈4,166,667 руб.

def calculate_net_income(gross_income):
    """
    Расчет НДФЛ для ежемесячного дохода по прогрессивной шкале (с 2025 года).
    Функция возвращает чистый доход за месяц и строку с информацией по ставкам.
    """
    tax = 0.0
    tax_rate_info_parts = []
    remaining = gross_income

    if remaining > 0:
        taxable = min(remaining, THRESHOLD1)
        tax += taxable * 0.13
        tax_rate_info_parts.append(f"13% на первые {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, THRESHOLD2 - THRESHOLD1)
        tax += taxable * 0.15
        tax_rate_info_parts.append(f"15% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, THRESHOLD3 - THRESHOLD2)
        tax += taxable * 0.18
        tax_rate_info_parts.append(f"18% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, THRESHOLD4 - THRESHOLD3)
        tax += taxable * 0.20
        tax_rate_info_parts.append(f"20% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = remaining
        tax += taxable * 0.22
        tax_rate_info_parts.append(f"22% на оставшиеся {taxable:.2f} руб.")
        remaining -= taxable

    net_income = gross_income - tax
    tax_rate_info = " ".join(tax_rate_info_parts)
    return net_income, tax_rate_info

def calculate_yearly_net_income(yearly_gross):
    """
    Расчет НДФЛ для годового дохода по прогрессивной шкале (годовые пороги).
    Годовые пороги:
      - 13%: до 2,400,000 руб.
      - 15%: от 2,400,000 до 5,000,000 руб.
      - 18%: от 5,000,000 до 20,000,000 руб.
      - 20%: от 20,000,000 до 50,000,000 руб.
      - 22%: свыше 50,000,000 руб.
    Функция возвращает чистый годовой доход и строку с информацией по ставкам.
    """
    threshold1 = 2400000
    threshold2 = 5000000
    threshold3 = 20000000
    threshold4 = 50000000
    tax = 0.0
    parts = []
    remaining = yearly_gross

    if remaining > 0:
        taxable = min(remaining, threshold1)
        tax += taxable * 0.13
        parts.append(f"13% на первые {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, threshold2 - threshold1)
        tax += taxable * 0.15
        parts.append(f"15% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, threshold3 - threshold2)
        tax += taxable * 0.18
        parts.append(f"18% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = min(remaining, threshold4 - threshold3)
        tax += taxable * 0.20
        parts.append(f"20% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    if remaining > 0:
        taxable = remaining
        tax += taxable * 0.22
        parts.append(f"22% на оставшиеся {taxable:.2f} руб.")
        remaining -= taxable

    net_yearly = yearly_gross - tax
    tax_info = " ".join(parts)
    return net_yearly, tax_info

def calculate_monthly_kpi_bonus(fixed_income, kpi_percentage, period_months):
    """
    Рассчитывает KPI премию для одного платежного периода.
    При этом KPI премия рассчитывается как:
      bonus_payment = fixed_income * (kpi_percentage / 100) * period_months
    """
    bonus_payment = fixed_income * (kpi_percentage / 100) * period_months
    return bonus_payment

@app.route('/', methods=['GET', 'POST'])
def index():
    # Результаты для отображения
    result_without_kpi = None
    result_with_kpi = None
    yearly_without_kpi = None
    yearly_with_kpi = None
    tax_info_without_kpi = None
    tax_info_with_kpi = None
    error = None
    form_data = {
        'base_salary': '',
        'fixed_bonus': '',
        'has_kpi': False,
        'kpi_percentage': '',
        'period_months': '3'  # значение по умолчанию (квартал)
    }

    if request.method == 'POST':
        form_data['base_salary'] = request.form.get('base_salary', '').strip()
        form_data['fixed_bonus'] = request.form.get('fixed_bonus', '').strip()
        form_data['has_kpi'] = request.form.get('has_kpi') == 'on'
        if form_data['has_kpi']:
            form_data['kpi_percentage'] = request.form.get('kpi_percentage', '').strip()
            form_data['period_months'] = request.form.get('period_months', '3').strip()
        else:
            form_data['kpi_percentage'] = '0'
            form_data['period_months'] = '0'

        if not form_data['base_salary']:
            error = "Поле 'Оклад' обязательно для заполнения."
        elif form_data['has_kpi'] and not form_data['kpi_percentage']:
            error = "Поле 'Процент KPI премии' обязательно для заполнения."
        else:
            try:
                base_salary = float(form_data['base_salary'])
                fixed_bonus = float(form_data['fixed_bonus']) if form_data['fixed_bonus'] else 0.0

                monthly_regular = base_salary + fixed_bonus
                regular_yearly = monthly_regular * 12

                # Если KPI включена, рассчитываем годовую сумму премии с учетом периодичности
                total_kpi_bonus = 0.0
                if form_data['has_kpi']:
                    kpi_percentage = float(form_data['kpi_percentage'])
                    period_months = int(form_data['period_months'])
                    # Количество выплат в году:
                    payments_per_year = 12 // period_months
                    # Каждая выплата KPI:
                    bonus_payment = calculate_monthly_kpi_bonus(monthly_regular, kpi_percentage, period_months)
                    total_kpi_bonus = payments_per_year * bonus_payment

                # Годовой общий валовый доход:
                yearly_gross = regular_yearly + total_kpi_bonus

                # Расчёт чистого дохода за месяц без KPI
                net_monthly_without, tax_info_without_kpi = calculate_net_income(monthly_regular)
                result_without_kpi = net_monthly_without

                # Расчёт годового чистого дохода без KPI
                yearly_without_kpi, _ = calculate_yearly_net_income(regular_yearly)

                if form_data['has_kpi']:
                    # При наличии KPI, рассчитываем "на руки" как: ежемесячный регулярный доход + (KPI бонус, полученный раз в месяц, если бы его распределяли равномерно)
                    # Но для годового расчёта берем общий годовой доход
                    net_yearly, tax_info_yearly = calculate_yearly_net_income(yearly_gross)
                    yearly_with_kpi = net_yearly
                    # Также можно рассчитать эквивалент ежемесячного дохода с KPI
                    result_with_kpi = (yearly_gross / 12) - ( (regular_yearly/12 - net_monthly_without) ) # примерное значение
                    tax_info_with_kpi = tax_info_yearly
            except Exception as e:
                error = f"Ошибка в вводе данных: {e}"

    return render_template('index.html',
                           result_without_kpi=result_without_kpi,
                           result_with_kpi=result_with_kpi,
                           yearly_without_kpi=yearly_without_kpi,
                           yearly_with_kpi=yearly_with_kpi,
                           tax_info_without_kpi=tax_info_without_kpi,
                           tax_info_with_kpi=tax_info_with_kpi,
                           error=error,
                           form_data=form_data)

if __name__ == '__main__':
    app.run(debug=True)
