# =============================================================================
# Load libraries
# =============================================================================

import catboost as cb
import numpy as np
import pandas as pd
import tempfile
from catboost import monoforest as cbmf
from catboost import utils as cbus
from matplotlib import pyplot as plt
from sklearn import base as snbe

# =============================================================================
# AbsoluteDifferenceCallback
# =============================================================================

class AbsoluteDifferenceCallback:
    def __init__(
        self, 
        metric_sr: str, 
        threshold_ft: float = 0.01):
        '''
        Stops training when difference between learn and validation metrics surpasses threshold
        
        Parameters
        ----------
        metric_sr : str
            Metric.
        threshold_ft : float, optional
            Threshold. The default is 0.01.
        
        Returns
        -------
        None.
        '''
        self.metric_sr = metric_sr
        self.threshold_ft = threshold_ft

    def after_iteration(
            self, 
            info):
        '''
        Checks whether to stop
        
        Parameters
        ----------
        info : TYPE
            DESCRIPTION.
        
        Returns
        -------
        continue_bl : bool
            Flag for whether to continue.
        '''
        learn_metric_ft = info.metrics['learn'][self.metric_sr][-1]
        validation_metric_ft = info.metrics['validation'][self.metric_sr][-1]
        difference_ft = abs(validation_metric_ft - learn_metric_ft)
        continue_bl = difference_ft < self.threshold_ft
        return continue_bl

# =============================================================================
# CatBoostClassifier
# =============================================================================

class CatBoostClassifier(cb.CatBoostClassifier):
    def fit(self, X, y, **kwargs):
        # Get params
        params_dt = self.get_params()

        # Update params
        params_dt = update_params(params_dt=params_dt, X=X)
        
        # Set params
        self.set_params(**params_dt)

        # Fit
        return super().fit(X=X, y=y, **kwargs)
    
# =============================================================================
# CatBoostInspector
# =============================================================================

class CatBoostInspector:
    def __init__(
            self, 
            cbm: cb.CatBoost, 
            metrics_lt: list):
        '''
        Inspects CatBoost model

        Parameters
        ----------
        cbm : cb.CatBoost
            Model.
        metrics_lt : list
            Metrics.

        Returns
        -------
        None.

        '''
        self.cbm = cbm
        self.metrics_lt = metrics_lt

    def fit(
            self, 
            X: pd.DataFrame, 
            y: pd.Series, 
            pool_dt: dict = dict()):
        '''
        Calculates metrics and feature importances

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.
        y : pd.Series
            Target vector.
        pool_dt : dict, optional
            Pool params. The default is dict().

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        # Get pool
        pool_dt['cat_features'] = self.cbm.get_params().get('cat_features', [])
        pl = cb.Pool(data=X, label=y, **pool_dt)

        # Get eval metrics
        self.eval_metrics_df = pd.DataFrame(
            data=self.cbm.eval_metrics(data=pl, metrics=self.metrics_lt))

        # Get thresholded metrics
        self.thresholded_metrics_df = pd.concat(objs=[
            pd.DataFrame(
                data=np.array(object=cbus.get_roc_curve(model=self.cbm, data=pl)), 
                index=['fpr', 'tpr', 'thresholds']).T.set_index(keys='thresholds'),
            pd.DataFrame(
                data=np.array(object=cbus.get_fnr_curve(model=self.cbm, data=pl)), 
                index=['thresholds', 'fnr']).T.set_index(keys='thresholds')
        ], axis=1)

        # Get feature importances
        features_lt = self.cbm.feature_names_
        feature_importances_df = pd.concat(objs=[
            pd.Series(
                data=self.cbm.get_feature_importance(data=pl, type=type_sr), 
                index=features_lt, 
                name=type_sr)
            for type_sr in ['PredictionValuesChange', 'LossFunctionChange']
        ], axis=1)
        feature_importances_df.sort_values(by='LossFunctionChange', ascending=False, inplace=True)
        self.feature_importances_df = feature_importances_df

        # Get interactions
        features_dt = {index_it: feature_sr for index_it, feature_sr in enumerate(iterable=features_lt)}
        interactions_df = pd.DataFrame(
            data=self.cbm.get_feature_importance(data=pl, type='Interaction'),
            columns=['first_feature', 'second_feature', 'interactions'])
        self.interactions_df = interactions_df.apply(
            func=lambda x: x.map(arg=features_dt) if x.name != 'interactions' else x)
        return self

    def plot_eval_metrics(
            self, 
            last_bl: bool):
        '''
        Plots eval metrics (either last ones or whole history)

        Parameters
        ----------
        last_bl : bool
            Flag for whether to return last metrics.

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        if last_bl:
            eval_metrics_ss = self.eval_metrics_df.iloc[-1, :].sort_values().rename(index='metrics')
            ax = eval_metrics_ss.plot(kind='barh')
            ax.axvline(c='k', ls=':')
            pd.plotting.table(
                ax=ax, 
                data=eval_metrics_ss.round(decimals=3), 
                bbox=[1.5, 0, 0.25, 0.1 * eval_metrics_ss.shape[0]])
        else:
            self.eval_metrics_df.plot(
                subplots=True, layout=(-1, 1), figsize=(10, 3 * self.eval_metrics_df.shape[1]));
        fig = plt.gcf()
        return fig

    def plot_roc_curve(self):
        '''
        Plots ROC curve

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        ax = self.thresholded_metrics_df.plot(
            x='fpr', y='tpr', ylabel='tpr', label='ROC curve', figsize=(5, 5))
        ax.plot([0, 1], [0, 1], 'k:', label='Chance')
        ax.legend()
        fig = ax.figure
        return fig

    def plot_fpr_fnr(self):
        '''
        Plots FPR and FNR for every threshold

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        ax = self.thresholded_metrics_df.plot(y=['fpr', 'fnr'])
        fig = ax.figure
        return fig

    def plot_feature_importances(self):
        '''
        Plots feature importances

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        axes = self.feature_importances_df.plot(subplots=True, layout=(-1, 1), figsize=(10, 10))
        for ax in axes.ravel():
            ax.axhline(c='k', ls=':')
            ax.set(xticks=[])
            column_sr = ax.get_legend().get_texts()[0]._text
            data_ss = self.feature_importances_df[column_sr].describe().round(decimals=3)
            pd.plotting.table(ax=ax, data=data_ss, bbox=[1.25, 0, 0.25, 1])
        fig = plt.gcf()
        return fig
    
    def plot_top_feature_importances(
            self, 
            nlargest_n_it: int = 10, 
            nlargest_columns_lt: list = ['LossFunctionChange']):
        '''
        Plots top feature importances

        Parameters
        ----------
        nlargest_n_it : int, optional
            Number of top importances. The default is 10.
        nlargest_columns_lt : list, optional
            Column on which to sort. The default is ['LossFunctionChange'].

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        (
            self.feature_importances_df
            .nlargest(n=nlargest_n_it, columns=nlargest_columns_lt)
            [::-1]
            .plot(kind='barh', subplots=True, layout=(1, -1), sharex=False, sharey=True, legend=False)
        )
        fig = plt.gcf()
        return fig

    def plot_interactions(self):
        '''
        Plots interactions

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        interactions_ss = self.interactions_df['interactions']
        ax = interactions_ss.plot()
        ax.axhline(c='k', ls=':')
        data_ss = interactions_ss.describe().round(decimals=3)
        pd.plotting.table(ax=ax, data=data_ss, bbox=[1.25, 0, 0.25, 1])
        fig = ax.figure
        return fig
    
    def plot_top_interactions(
            self, 
            nlargest_n_it: int = 10):
        '''
        Plots top interactions

        Parameters
        ----------
        nlargest_n_it : int, optional
            Number of top interactions. The default is 10.

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        ax = (
            self.interactions_df
            .set_index(keys=['first_feature', 'second_feature'])
            .squeeze()
            .nlargest(n=nlargest_n_it)
            [::-1]
            .plot(kind='barh'))
        fig = ax.figure
        return fig
    
# =============================================================================
# CatBoostRegressor
# =============================================================================

class CatBoostRegressor(cb.CatBoostRegressor):
    def fit(self, X, y, **kwargs):
        # Get params
        params_dt = self.get_params()

        # Update params
        params_dt = update_params(params_dt=params_dt, X=X)
        
        # Set params
        self.set_params(**params_dt)

        # Fit
        return super().fit(X=X, y=y, **kwargs)
    
# =============================================================================
# default_params_dt
# =============================================================================
    
default_params_dt = dict(
    early_stopping_rounds=10, 
    eval_fraction=0.2,
    train_dir=tempfile.tempdir, 
    use_best_model=True, 
    verbose=100) 
    
# =============================================================================
# MonoForestInspector
# =============================================================================

class MonoForestInspector:
    def __init__(
            self,
            cbm: cb.CatBoost):
        '''
        Inspects monoforest

        Parameters
        ----------
        cbm : cb.CatBoost
            Model.

        Returns
        -------
        None.

        '''
        self.cbm = cbm

    def fit(self):
        '''
        Calculates polynomials and splits

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        # Get polynomials list
        polynom_lt = cbmf.to_polynom(model=self.cbm)

        # Get it as data frame
        self.polynom_df = (
            pd.DataFrame(data=list(map(lambda x: x.__dict__, polynom_lt)))
            .assign(value = lambda x: x['value'].apply(func=lambda x: x[0])))

        # Get splits
        splits_dt = (
            self.polynom_df['splits']
            .apply(func=pd.Series)
            .stack()
            .apply(func=lambda x: x.__dict__)
            .to_dict())
        
        # Get them as data frame
        self.features_dt = {
            index_it: feature_sr 
            for index_it, feature_sr in enumerate(iterable=self.cbm.feature_names_)}
        self.splits_df = (
            pd.DataFrame(data=splits_dt)
            .T
            .assign(feature_idx = lambda x: x['feature_idx'].map(arg=self.features_dt)))
        return self

    def plot_weight(self):
        '''
        Plots weights

        Returns
        -------
        fig : plt.Figure
            Figure.

        '''
        weight_ss = self.polynom_df['weight']
        ax = weight_ss.sort_values(ascending=False).reset_index(drop=True).plot()
        ax.axhline(c='k', ls=':')
        data_ss = weight_ss.describe().round(decimals=3)
        pd.plotting.table(ax=ax, data=data_ss, bbox=[1.25, 0, 0.25, 1])
        fig = ax.figure
        return fig
    
# =============================================================================
# update_params
# =============================================================================

def update_params(
        params_dt: dict, 
        X: pd.DataFrame):
    '''
    Updates params (e.g., as part of pipeline)

    Parameters
    ----------
    params_dt : dict
        Params at initialization.
    X : pd.DataFrame
        Current feature matrix.

    Returns
    -------
    params_dt : dict
        Params.

    '''
    # Get cat features
    old_cat_features_lt = params_dt.get('cat_features', [])
    new_cat_features_lt = (
        X.columns
        .intersection(other=old_cat_features_lt)              # May have been dropped
        .union(other=X.select_dtypes(include=object).columns) # May have been added
        .tolist())

    # Get monotone contraints
    old_monotone_constraints_dt = params_dt.get('monotone_constraints', dict())
    if old_monotone_constraints_dt:
        new_monotone_constraints_dt = {
            key_sr: value_it for key_sr, value_it in old_monotone_constraints_dt.items()
            if key_sr in X.columns}
    else:
        new_monotone_constraints_dt = old_monotone_constraints_dt

    # Update
    params_dt.update(
        cat_features=new_cat_features_lt, 
        monotone_constraints=new_monotone_constraints_dt)
    return params_dt
