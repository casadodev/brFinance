import datetime

import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
from pandas.errors import ParserError
from requests import Response


class SearchCurrencyPrice:

    def __init__(self, currency_code: int, initial_date: datetime.date, final_date: datetime.date):
        """
        Parameters
        ----------
        currency_code : int
            Currency code according to available currencies method
        initial_date: str
            Ex: 01/01/2021
        final_date: str
            Ex: 30/07/2021
        """
        assert final_date > initial_date, "Final date is earlier than initial date"

        self.currency_code = currency_code
        self.initial_date = initial_date.strftime("%d/%m/%Y")
        self.final_date = final_date.strftime("%d/%m/%Y")

    def _fetch_data(self) -> pd.DataFrame:
        """
        Returns
        -------
        pandas.Dataframe
            Dataframe with raw data coming from Central Bank website
        """
        url = f'https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?method=gerarCSVFechamentoMoedaNoPeriodo' \
              f'&ChkMoeda={self.currency_code}&DATAINI={self.initial_date}&DATAFIM={self.final_date}'
        
        try:
            df = pd.read_csv(url, sep=";", encoding="latin", decimal=",", index_col=0,
                             names=["Date", "Tipo", "Moeda", "Compra", "Venda"], usecols=[0, 2, 3, 4, 5])
            
        except ParserError:
            raise Exception("An error occurred when parsing data. Check if currency is available at "
                            "https://www.bcb.gov.br/estabilidadefinanceira/historicocotacoes")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        df : pandas.Dataframe
            Dataframe with raw data coming from Central Bank website

        Returns
        -------
        pandas.Dataframe
            Dataframe with cleaned data
        """
        df.index = pd.to_datetime([str(x).zfill(8) for x in df.index], format="%d%m%Y", errors='coerce')

        df["Compra"] = pd.to_numeric(df["Compra"].astype(str).str.replace(',', '.'))
        df["Venda"] = pd.to_numeric(df["Venda"].astype(str).str.replace(',', '.'))

        df.sort_index(inplace=True)
        
        return df

    def _check_if_code_exists(self) -> bool:
        """
        Returns
        -------
        bool
            True if Currency code exists, otherwise False
        """
        df = SearchAvailableCurrencies().get_available_currencies()

        return bool(len(df[df["Code"] == str(self.currency_code)]))

    def get_data(self) -> pd.DataFrame:
        """
        Returns
        -------
        pandas.Dataframe
            Dataframe with prices of a specific currency in respect to Brazilian Real
        """
        assert self._check_if_code_exists(), "Currency code does not exist"

        pure_df = self._fetch_data()
        clean_df = self._clean_data(pure_df)

        return clean_df


class SearchAvailableCurrencies:

    def _fetch_data(self) -> Response:
        """
        Returns
        -------
        Response
            Response from Central Bank website
        """
        url = 'https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?method=exibeFormularioConsultaBoletim'
        page = requests.get(url)

        return page

    def _clean_data(self, page: Response) -> pd.DataFrame:
        """
        Parameters
        ----------
        page : Response
            Response from Central Bank website

        Returns
        -------
        pandas.Dataframe
            Dataframe with cleaned data
        """
        soup = BeautifulSoup(page.content, 'html.parser')
        options = soup.find_all("option")

        options_dict = [(option.get_text(), option.get("value")) for option in options]

        df = pd.DataFrame.from_records(options_dict, columns=['Currency', 'Code'])

        return df

    def get_available_currencies(self) -> pd.DataFrame:
        """
        Returns
        -------
        pandas.Dataframe
            Dataframe with available currencies and respective codes
        """
        page = self._fetch_data()
        df = self._clean_data(page)

        return df


class SearchAllCurrenciesPrices:

    def __init__(self,
                 reference_date: datetime.date = datetime.datetime.now()):
        """
        Parameters
        ----------
        currency_code : int
            Currency code according to available currencies method
        initial_date: str
            Ex: 01/01/2021
        final_date: str
            Ex: 30/07/2021
        """

        assert reference_date <= datetime.datetime.now(), "Final date is should be earlier than today"

        self.reference_date = reference_date.strftime("%Y%m%d")

    def _fetch_data(self) -> pd.DataFrame:
        """
        Returns
        -------
        pandas.Dataframe
            Dataframe with raw data coming from Central Bank website
        """
        

        url = f'https://www4.bcb.gov.br/Download/fechamento/{self.reference_date}.csv'
        print(url)


        columns = ["Reference Date",
                   "Código",
                   "Tipo",
                   "Moeda",
                   "Cotações em Real - Compra",
                   "Cotações em Real - Venda",
                   "Paridade - Compra",
                   "Paridade - Venda"]

        df = pd.DataFrame(columns=columns)

        try:
            df = pd.read_csv(url, sep=";",
                             encoding="latin",
                             decimal=",",
                             names=columns,
                             usecols=[0, 1, 2, 3, 4, 5, 6, 7])
            
        except Exception as exp:
            if 'HTTP Error 404: Not Found' in str(exp):
                print(f"Currency is not available for this date: {self.reference_date}, {url}")
            else:
                raise

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        df : pandas.Dataframe
            Dataframe with raw data coming from Central Bank website

        Returns
        -------
        pandas.Dataframe
            Dataframe with cleaned data
        """
        
        df["Reference Date"] = pd.to_datetime(df["Reference Date"], format="%d/%m/%Y", errors='coerce')
        df.set_index("Reference Date", drop=True, append=False, inplace=True)

        for column in ["Cotações em Real - Compra",
                       "Cotações em Real - Venda",
                       "Paridade - Compra",
                       "Paridade - Venda"]:
            df[column] = pd.to_numeric(df[column].astype(str).str.replace(',', '.'), errors='coerce')

        return df

    def get_prices(self) -> pd.DataFrame:
        """
        Returns
        -------
        pandas.Dataframe
            Dataframe with today prices of all currencies in respect to Brazilian Real
        """
        pure_df = self._fetch_data()
        clean_df = self._clean_data(pure_df)
        
        return clean_df

