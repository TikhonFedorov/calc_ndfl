from flask import Flask, render_template, request

app = Flask(__name__)

# Месячные пороги (годовые пороги делим на 12)
THRESHOLD1 = 2_400_000 / 12       # 200,000 руб.
THRESHOLD2 = 5_000_000 / 12       # ≈416,667 руб.
THRESHOLD3 = 20_000_000 / 12      # ≈1,666,667 руб.
THRESHOLD4 = 50_000_000 / 12      # ≈4,166,667 руб.

def calculate_net_income(gross_income):
    """
    Расчет НДФЛ по новой прогрессивной шкале (с 2025 года) для ежемесячного дохода.
    Повышенные ставки применяются только к сумме, превышающей соответствующий порог.
    Функция возвращает чистый доход и строку с информацией по применённым ставкам.
    """
    tax = 0.0
    tax_rate_info_parts = []
    remaining = gross_income

    # Первый диапазон: до THRESHOLD1
    if remaining > 0:
        taxable = min(remaining, THRESHOLD1)
        tax += taxable * 0.13
        tax_rate_info_parts.append(f"13% на первые {taxable:.2f} руб.")
        remaining -= taxable

    # Второй диапазон: от THRESHOLD1 до THRESHOLD2
    if remaining > 0:
        taxable = min(remaining, THRESHOLD2 - THRESHOLD1)
        tax += taxable * 0.15
        tax_rate_info_parts.append(f"15% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    # Третий диапазон: от THRESHOLD2 до THRESHOLD3
    if remaining > 0:
        taxable = min(remaining, THRESHOLD3 - THRESHOLD2)
        tax += taxable * 0.18
        tax_rate_info_parts.append(f"18% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    # Четвертый диапазон: от THRESHOLD3 до THRESHOLD4
    if remaining > 0:
        taxable = min(remaining, THRESHOLD4 - THRESHOLD3)
        tax += taxable * 0.20
        tax_rate_info_parts.append(f"20% на следующие {taxable:.2f} руб.")
        remaining -= taxable

    # Пятый диапазон: свыше THRESHOLD4
    if remaining > 0:
        taxable = remaining
        tax += taxable * 0.22
        tax_rate_info_parts.append(f"22% на оставшиеся {taxable:.2f} руб.")
        remaining -= taxable

    net_income = gross_income - tax
    tax_rate_info = " ".join(tax_rate_info_parts)
    return net_income, tax_rate_info

def calculate_monthly_kpi_bonus(fixed_income, kpi_percentage, period_months):
    """
    Рассчитывает KPI премию как процент от совокупного дохода (оклад+фиксированная премия)
    за период, затем распределяет равномерно на месяцы.
    """
    monthly_income = fixed_income
    total_kpi_bonus = monthly_income * (kpi_percentage / 100) * period_months
    monthly_kpi_bonus = total_kpi_bonus / period_months
    return monthly_kpi_bonus

@app.route('/', methods=['GET', 'POST'])
def index():
    result_without_kpi = None
    result_with_kpi = None
    tax_info_without_kpi = None
    tax_info_with_kpi = None
    error = None
    # Передаем значения для заполнения полей (если они есть)
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
        # Если чекбокс выбран, считываем KPI данные, иначе оставляем 0
        if form_data['has_kpi']:
            form_data['kpi_percentage'] = request.form.get('kpi_percentage', '').strip()
            form_data['period_months'] = request.form.get('period_months', '3').strip()
        else:
            form_data['kpi_percentage'] = '0'
            form_data['period_months'] = '0'

        # Валидация: оклад обязательно должен быть заполнен
        if not form_data['base_salary']:
            error = "Поле 'Оклад' обязательно для заполнения."
        else:
            try:
                base_salary = float(form_data['base_salary'])
                # Если поле фиксированной премии пустое, считаем 0
                fixed_bonus = float(form_data['fixed_bonus']) if form_data['fixed_bonus'] else 0.0

                monthly_income_without_kpi = base_salary + fixed_bonus

                # Если KPI премия есть, рассчитываем её
                monthly_kpi_bonus = 0.0
                if form_data['has_kpi']:
                    kpi_percentage = float(form_data['kpi_percentage']) if form_data['kpi_percentage'] else 0.0
                    period_months = int(form_data['period_months'])
                    monthly_kpi_bonus = calculate_monthly_kpi_bonus(monthly_income_without_kpi, kpi_percentage, period_months)

                monthly_income_with_kpi = monthly_income_without_kpi + monthly_kpi_bonus

                net_without, tax_info_without_kpi = calculate_net_income(monthly_income_without_kpi)
                result_without_kpi = net_without

                if form_data['has_kpi']:
                    net_with, tax_info_with_kpi = calculate_net_income(monthly_income_with_kpi)
                    result_with_kpi = net_with
            except Exception as e:
                error = f"Ошибка в вводе данных: {e}"

    return render_template('index.html',
                           result_without_kpi=result_without_kpi,
                           result_with_kpi=result_with_kpi,
                           tax_info_without_kpi=tax_info_without_kpi,
                           tax_info_with_kpi=tax_info_with_kpi,
                           error=error,
                           form_data=form_data)

if __name__ == '__main__':
    app.run(debug=True)
