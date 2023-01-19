class CurrencyConverter:
    def __init__(self):
        self.rates = {}

    # function to do a simple cross multiplication between
    # the amount and the conversion rates
    def convert(self, from_currency, to_currency, amount):
        initial_amount = amount
        try:
            if from_currency == 'USD':  # From USD to another currency
                amount = int(amount * self.rates[to_currency])
            else:
                amount = int(amount * 1 / self.rates[from_currency])
            # print('{} {} = {} {}'.format(initial_amount, from_currency, amount, to_currency))
        except KeyError:
            print('Unknown Currency Rate: {} to {}'.format(from_currency, to_currency))
            pass
        return amount
