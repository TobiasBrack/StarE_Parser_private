function data = get_stare_data_eJust_3( fname )
% -------------------------------------------------------------------------
%
% fname: StarE Resultat Ascii Export
%
% data: Array von Strukturen mit:
%           - Kurvenname
%           - normalized Enthalpie
%           - Onset
%           - Step
%           - Heating Rate
%           - Info Sample
%           - Sample mass
%           - Curve Values
%           - Adjust Parameters
%           - Sample Holder
%           - Signal Value
%
% T.Hütter, 24.01.2015
% 
% V6
% Signal value 
% T.Hütter, 03.08.2016
%
% eJust
% adapted to names and data needed for electrical adjustment DSC
% T.Meyer, 16.11.2020
% adapted for Stare 17.00 T2
% T.Meyer, 27.01.2021
% adapted for Stare 18.00a, DSC und TGS HF data
% T.Meyer, 11.03.2024
%

%% open file
fid = fopen( fname );


%% curve index
i = 0;


%% skip lines until first curve
C = textscan( fid, '%s', 1,  'delimiter', '\n'); s = C{1}{1};
while ~strcmp( s, 'Curve Name:' )
    C = textscan( fid, '%s', 1, 'delimiter', '\n');
    s = C{1}{1};
end 


%% repeat until end of file
while ~feof( fid )
    
    % Curve Index
    i = i + 1;
    
    % Initialize data fields
    data(i).h = []; data(i).Tonset = []; data(i).Slope = []; data(i).step = []; data(i).beta = []; data(i).value = [];
    data(i).Eind = []; data(i).Erel = []; data(i).p_R = []; data(i).p_TauLag = []; data(i).EIn = []; data(i).CIn = [];
    data(i).dEr = []; data(i).dCr = []; data(i).performed = []; data(i).sample_holder = [];
    data(i).sample_holder_material = []; data(i).GasF = []; data(i).type = [];
    
    % Curve name
    C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};
    data(i).curve_name = s;
    
    % performed date
    C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};
    if strfind( s, 'Performed' ) 
        data(i).performed = s; % tbd: tranfer to date format wuird nicht in jedem Fall eingetragen??
        C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};
    end
    
    % type
    if ~strcmp( s, 'Curve Values:' )
        data(i).type = s;        % type wird nicht immer geschrieben
        C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};
    end
    
    while ~strcmp( s, 'Curve Name:' ) && ~feof( fid )
        
%         disp(s)
%         pause
        if strfind( s, 'Curve Values:' )
            C = textscan( fid, '%s', 2, 'delimiter', '\n');
            C = textscan( fid, '%f%f%f%f%f' );
            data(i).curve_values = cell2mat( C );                    
            C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};    % neue Zeile

        elseif strfind( s, 'Sample:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n'); data(i).sample = C{1}{1};
            data(i).m_sample = '';
            if ~isempty( data(i).sample )
                C = textscan( data(i).sample, '%s' );
                x = C{1}; data(i).m_sample = str2num(x{end-1});
            end
            C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};    % neue Zeile

        elseif strfind( s, 'Sample Holder:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            while (~isempty(s) && (s(1)==' '))
                if strfind( s, 'Weight'), data(i).sample_holder = strip( s ); end
                if strfind( s, 'Material'), data(i).sample_holder_material = strip( s ); end
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            end
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end

            
        elseif strfind( s, 'Sample Remarks:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
            
        elseif strfind( s, 'Material Class:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
            
        elseif strfind( s, 'Experiment Comments:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
            
        elseif strfind( s, 'Results:' )
            while (s(1)==' ') && ~isempty( s )
                %                 if strfind( s, 'normalized' )
                if strfind( s, 'normalized' )
                    S = textscan( s, '%s%f%s' ); data(i).h = [ data(i).h S{2} ];
                elseif strfind( s, 'Onset' )
                    S = textscan( s, '%s%f%s' ); data(i).Tonset = [ data(i).Tonset S{2} ];
                elseif strfind( s, 'Slope' )
                    S = textscan( s, '%s%f%s' ); data(i).Slope = [ data(i).Slope S{2} ];
                elseif strfind( s, 'Step' )
                    S = textscan( s, '%s%f%s' ); data(i).step = [ data(i).step S{2} ];
                elseif strfind( s, 'Heating Rate' )
                    S = textscan( s, '%s%s%f%s' ); data(i).beta = [ data(i).beta S{3} ];                    
                elseif strfind( s, 'Signal Value' )
                    S = textscan( s, '%s%s%f%s' ); data(i).value = [ data(i).value S{3} ];
                end
                C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};
                if strcmp( s, '?' ), s = s(k+1:end); end % unvalid result
            end
            C = textscan( fid, '%s', 1, 'delimiter', '\n'); s = C{1}{1};    % neue Zeile
           
        elseif strfind( s, 'Texts:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1}; % empty line
            while (isempty( s ) || s(1)==' ')
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            end
        
        elseif strfind( s, 'Adjustment:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1}; % ignore line
            while ~isempty( s ) && (s(1)==' ')
                if strfind( s, 'Gas Factor    :')
                    C = textscan( s, '%s' ); x = C{1};
                    data(i).GasF = str2num(x{end});
                elseif strfind( s, 'E Indium      :')
                    C = textscan( s, '%s' ); x = C{1};
                    data(i).E_Indium = str2num(x{end-1});
                elseif strfind( s, 'EIn:')
                    C = textscan( s, '%s' ); x = C{1};
                    data(i).EIn = str2num(x{end});
                elseif strfind( s, 'CIn:')
                    C = textscan( s, '%s' ); x = C{1};
                    data(i).CIn = str2num(x{end});
                elseif strfind( s, 'dEr:')
                    C = textscan( s, '%s%f%f%f%f%f:%f%f' );
                    data(i).dEr = cell2mat({C{2:end}});
                elseif strfind( s, 'dCr:')
                    C = textscan( s, '%s%f%f%f%f%f:%f%f' );
                    data(i).dCr = cell2mat({C{2:end}});
                elseif strfind( s, 'Cell Temperature: Pt100' )
                    C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
                    S = textscan( s, '%s%s%f%s%f%s%s%f%s%s' );
                    p_R=[ S{3} S{5} S{8}];
                    x=char(S{4}); if x == '-' p_R(2)=-p_R(2); end
                    x=char(S{7}); if x == '-' p_R(3)=-p_R(3); end
                    data(i).p_R = [data(i).p_R; fliplr(p_R)];
                elseif strfind( s, 'Tau Lag     :' )
                    S = textscan( s, '%s  %s      %s %f    %s %f    %s     %s %f %s  %s' );
                    p_TauLag=[ S{4} S{6} S{9}];
                    x=char(S{5}); if x == '-' p_TauLag(2)=-p_TauLag(2); end
                    x=char(S{8}); if x == '-' p_TauLag(3)=-p_TauLag(3); end
                    data(i).p_TauLag = [data(i).p_TauLag; fliplr(p_TauLag)];
                elseif strfind( s, 'E Indium' )
                    S = textscan( s, '%s%s%s%f%s' ); data(i).Eind = [ data(i).Eind S{4} ];
                elseif strfind( s, 'dE relative' )
                    S = textscan( s, '%s%s%s%f %s%f%s %s%f%s' );
                    Erel=[ S{4} S{6} S{9}];
                    x=char(S{5}); if x == '-' Erel(2)=-Erel(2); end
                    x=char(S{8}); if x == '-' Erel(3)=-Erel(3); end
                    data(i).Erel = [data(i).Erel; Erel];
                end
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            end
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            
        elseif strfind( s, 'User:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            if (~isempty(s) && (s(1)==' '))
                data(i).user = textscan( s, '%s' );
            end
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
            
        elseif strfind( s, 'Method:' )
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            if (~isempty(s) && (s(1)==' '))
                data(i).method = textscan( s, '%s' );
            end
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
            
        elseif (s(1)~=' ')  % unbekannte Einträge überlesen
            C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};
            while isempty( s ) || (s(1)==' ')  % lesen bis Text linksbündig
                C = textscan( fid, '%s', 1, 'delimiter', '\n', 'whitespace', ''); s = C{1}{1};    % neue Zeile
            end
        end
        
    end
    
end

%% close file
fclose(fid);
