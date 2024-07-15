## This section contains the textual strings used in the explorer.py

HOME_HEADING_STRING = """
<h1>Welcome to the Stingray Explorer Dashboard</h1>
"""

WELCOME_MESSAGE_STRING = """
<div>
    <p>This dashboard is designed to provide a comprehensive toolset for X-ray astronomy data analysis. Here are the main features:</p>
    <ul>
        <li><b>Quicklook with Stingray:</b><ul><li> Don't want to dabble around too much and generate plots fast and easy, this is the way.</li></ul></li>
        <li><b>Working with Event Data:</b> 
            <ul>
                <li>Setup and creating EventList from photon arrival times</li>
                <li>Roundtrip to Astropy-compatible formats</li>
                <li>Loading and writing EventList objects</li>
                <li>Simulating EventList from Lightcurve</li>
                <li>Joining EventLists</li>
            </ul>
        </li>
        <li><b>Working with Lightcurves:</b> 
            <ul>
                <li>Creating light curves from time stamps, counts, or photon arrival times</li>
                <li>Operations including addition, subtraction, indexing, and plotting</li>
                <li>Handling Good Time Intervals (GTIs) and analyzing light curve segments</li>
            </ul>
        </li>
        <li><b>Fourier Analysis:</b> 
            <ul>
                <li>Generating Powerspectra, AveragedPowerspectra, and Cross Spectra</li>
                <li>Normalizing and re-binning power spectra</li>
                <li>Creating Dynamical Power Spectra</li>
            </ul>
        </li>
        <li><b>Cross and Autocorrelations:</b> 
            <ul>
                <li>Generating CrossCorrelation and AutoCorrelation plots</li>
            </ul>
        </li>
        <li><b>Bispectra:</b> 
            <ul>
                <li>Understanding and plotting Bispectrum</li>
            </ul>
        </li>
        <li><b>Bayesian Excess Variance:</b> 
            <ul>
                <li>Theoretical background and practical examples</li>
            </ul>
        </li>
        <li><b>Multi-taper Periodogram:</b> 
            <ul>
                <li>Creating and analyzing Multitaper objects</li>
            </ul>
        </li>
        <li><b>Lomb Scargle Spectra:</b> 
            <ul>
                <li>Generating Lomb Scargle Powerspectrum and Crossspectrum</li>
            </ul>
        </li>
    </ul>
    <p>Please use the sidebar to navigate to the different analysis tools. Each tool comes with interactive widgets to customize your analysis and generate plots on the fly.</p>
    <p>We hope you find this dashboard useful for your research!</p>
</div>
"""

FOOTER_STRING = """
    <div>
        <p>Stingray Explorer Dashboard</p>
        <p>&copy; 2021 Kartik Mandar</p>
    </div>
    """