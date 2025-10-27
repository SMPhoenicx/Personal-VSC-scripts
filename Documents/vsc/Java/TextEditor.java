package Java;

import javax.swing.*;
import javax.swing.event.*;
import javax.swing.filechooser.FileSystemView;
import java.io.*;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.event.*;

import javax.swing.text.AttributeSet;
import javax.swing.text.BadLocationException;
import javax.swing.text.DefaultHighlighter;
import javax.swing.text.DefaultStyledDocument;
import javax.swing.text.Document;
import javax.swing.text.Highlighter;
import javax.swing.text.Style;
import javax.swing.text.StyleConstants;
import javax.swing.text.StyleContext;
import javax.swing.text.StyledDocument;

import java.util.HashMap;

class TextEditor extends JFrame implements ActionListener, DocumentListener //listeners for actions
{
    JFrame frame; //entire frame
    JMenuBar mb; //menu bar where actions are stored
    JTextPane txt; //text box for input
    JScrollPane jscroll; //helps the text pane scroll
    JFrame findMenu; //frame for search menu
    JTextField tf; //text area for search menu
    Stack unStack; //stack for undo
    Stack reStack; //stack for redo
    JButton sb; //maybe put these in the method only, not in the class
    JButton fleft; //buttons for iterating through caret positions
    JButton fright;
    DoubleCircLinkedList<Integer> dlist; //keeps track of caret positions
    JPanel jp; //where the search menu is stored
    Font arial; //fonts
    Font tnr;
    Style defaultStyle; //style
    HashMap<String, AttributeSet> keyStyles;
    long ogTime; //keeps track of time when last bit of information was added
    long secTime; //keeps track of new time, when text is updated
    String selectedFont; //keeps track of which font is currently seelected
    boolean codeMode; //whether code mode is on or not
    JMenuItem mode; //code mode or normal mode

    TextEditor() //initializes everything
    {
        selectedFont = "Arial"; //sets initial font
        codeMode = false; //not coding mode intially
        unStack = new Stack(20); //initialize stacks
        reStack = new Stack(20);
        //initialize all variables
        constructMenuBar(); 
        constructFindMenu();
        constructHashMap();
        constructFrame();
        ogTime = -1;
    }

    public void constructHashMap()
    {
        //initilaize default style
        StyleContext styleContext = StyleContext.getDefaultStyleContext();
        defaultStyle = StyleContext.getDefaultStyleContext().getStyle(StyleContext.DEFAULT_STYLE);
        
        // set keywords and their corresponding style attributes
        keyStyles = new HashMap<>();
        keyStyles.put("int", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.MAGENTA));
        keyStyles.put("float", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.MAGENTA));
        keyStyles.put("double", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.MAGENTA));
        keyStyles.put("String", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.YELLOW));
        keyStyles.put("if", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.BLUE));
        keyStyles.put("else", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.BLUE));
        keyStyles.put("for", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.BLUE));
        keyStyles.put("while", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.BLUE));
        keyStyles.put("return", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.BLUE));
        keyStyles.put("(", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.YELLOW));
        keyStyles.put(")", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.YELLOW));
        keyStyles.put("{", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.MAGENTA));
        keyStyles.put("}", styleContext.addAttribute(styleContext.getEmptySet(), StyleConstants.Foreground, Color.MAGENTA));
    
    }

    public void constructMenuBar()
    {
        //init menu bar
        mb = new JMenuBar();
        //all menus
        JMenu file = new JMenu("File");
        JMenu edit = new JMenu("Edit");
        JMenu format = new JMenu("Format");
        JMenu font = new JMenu("Font");
        JMenu fontSize = new JMenu("Font Size");
        //all submenus
        JMenuItem n = new JMenuItem("New");
        JMenuItem o = new JMenuItem("Open");
        JMenuItem p = new JMenuItem("Print");
        JMenuItem cut= new JMenuItem("Cut");
        JMenuItem copy = new JMenuItem("Copy");
        JMenuItem paste = new JMenuItem("Paste");
        JMenuItem undo = new JMenuItem("Undo");
        JMenuItem redo = new JMenuItem("Redo");
        JMenuItem FandR = new JMenuItem("FNR");
        JMenuItem fArial = new JMenuItem("Arial"); 
        JMenuItem fTNR = new JMenuItem("Times New Roman");
        JMenuItem f6 = new JMenuItem("6"); 
        JMenuItem f8 = new JMenuItem("8");
        JMenuItem f10 = new JMenuItem("10"); 
        JMenuItem f12 = new JMenuItem("12");
        JMenuItem f24 = new JMenuItem("24");
        JMenuItem f48 = new JMenuItem("48");
        mode = new JMenuItem("Code Mode: OFF");
        //all action listeners
        n.addActionListener(this);
        o.addActionListener(this);
        p.addActionListener(this);
        copy.addActionListener(this);
        paste.addActionListener(this);
        cut.addActionListener(this);
        undo.addActionListener(this);
        redo.addActionListener(this);
        FandR.addActionListener(this);
        fArial.addActionListener(this);
        fTNR.addActionListener(this);
        f6.addActionListener(this);
        f8.addActionListener(this);
        f10.addActionListener(this);
        f12.addActionListener(this);
        f24.addActionListener(this);
        f48.addActionListener(this);
        mode.addActionListener(this);
        //add submenus to menus
        file.add(n);
        file.add(o);
        file.add(p);
        edit.add(cut);
        edit.add(copy);
        edit.add(paste);
        edit.addSeparator();
        edit.add(undo);
        edit.add(redo);
        edit.addSeparator();
        edit.add(FandR);
        format.add(font);
        format.add(fontSize);
        format.add(mode);
        font.add(fArial);
        font.add(fTNR);
        fontSize.add(f6);
        fontSize.add(f8);
        fontSize.add(f10);
        fontSize.add(f12);
        fontSize.add(f24);
        fontSize.add(f48);
        //add menus to menu bar
        mb.add(file);
        mb.add(edit);
        mb.add(format);
        //set accelerators or shortcuts
        n.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_4, InputEvent.CTRL_DOWN_MASK));
        copy.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_1, InputEvent.CTRL_DOWN_MASK));
        paste.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_2, InputEvent.CTRL_DOWN_MASK));
        cut.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_3, InputEvent.CTRL_DOWN_MASK));
        o.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_5, InputEvent.CTRL_DOWN_MASK));
        undo.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_6, InputEvent.CTRL_DOWN_MASK));
        redo.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_7, InputEvent.CTRL_DOWN_MASK));
        FandR.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_8, InputEvent.CTRL_DOWN_MASK));
        p.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_9, InputEvent.CTRL_DOWN_MASK));
    }

    public void constructFrame()
    {
        //text area setup
        txt = new JTextPane();
        txt.getDocument().putProperty("JTextComponent", txt);
        txt.getDocument().addDocumentListener(this);
        //scroll setup
        jscroll = new JScrollPane(txt);
        jscroll.setBounds(200,200,700,700);
        //frame setup
        frame = new JFrame("Notepad--");
        frame.setSize(500,500);
        frame.setJMenuBar(mb);
        frame.setLocationRelativeTo(null);
        frame.getContentPane().add(jscroll);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setVisible(true);
    }

    public void constructFindMenu()
    {
        dlist = new DoubleCircLinkedList<Integer>(); //initialize variables
        sb = new JButton("Search");
        sb.addActionListener(this);
        fleft = new JButton("<");
        fright = new JButton(">");
        //set sizes for buttons
        sb.setSize(75, 200);
        fleft.setSize(50,50);
        fright.setSize(50,50);
        //add action listeners to buttons
        sb.addActionListener(this);
        fleft.addActionListener(this);
        fright.addActionListener(this);
        //setup search area and add to frame
        jp = new JPanel();
        jp.setLayout(new FlowLayout());
        findMenu = new JFrame();
        findMenu.setSize(300, 100);
        findMenu.setResizable(false);
        tf = new JTextField(10);
        jp.add(tf);
        jp.add(sb);
        jp.add(fleft);
        jp.add(fright);
        findMenu.add(jp, BorderLayout.CENTER);
        //add window listener to take away highlights when the frame is closed
        findMenu.addWindowListener(new WindowAdapter()
        {
            @Override
            public void windowClosing(WindowEvent e) {
                txt.getHighlighter().removeAllHighlights();
            }
        });
    }

    public void createFont(int size) //used for setting font sizes, creates font and then sets it
    {
        arial = new Font("Arial", Font.PLAIN, size);
        tnr = new Font("Times New Roman", Font.PLAIN, size);

        setFont(selectedFont);
    }

    public void setFont(String font) //used for setting the font in the frame
    {
        switch(font)
        {
            case "Arial":
                txt.setFont(arial);
                selectedFont = font;
                break;
            case "Times New Roman":
                txt.setFont(tnr);
                selectedFont = font;
                break;
        }
    }
    
    public void insertUpdate(DocumentEvent e)
    {
        if(ogTime == -1) //first input, saves copy, sets time
        {
            saveCopy();
            ogTime = System.currentTimeMillis();
        }
        else //following inputs
        {
            secTime = System.currentTimeMillis(); //checks time

            if(secTime - ogTime >= 5000) //if it's been more than 5 seconds, save the copy for undo/redo
            {
                saveCopy();
                ogTime = System.currentTimeMillis(); //set new time
            }
        }
        if(codeMode) highlightInBack();//if code mode is on, highlight
    }
    public void removeUpdate(DocumentEvent e)
    {
        if(ogTime == -1) //same as insertUpdate
        {
            saveCopy();
            ogTime = System.currentTimeMillis();
        }
        else
        {
            secTime = System.currentTimeMillis();

            if(secTime - ogTime >= 5000) //if it's been more than 5 seconds, save the copy for undo/redo
            {
                saveCopy();
                ogTime = System.currentTimeMillis();
            }
        }
       if(codeMode) highlightInBack(); //if code mode is on, highlight
    }
    public void changedUpdate(DocumentEvent e)
    { //does nothing
    }

    public void saveCopy()
    {
        Document copy = new DefaultStyledDocument(); 
        try {
            copy.insertString(0, txt.getText(), null); //make a deep copy of the document
            unStack.push(copy); //push to undo stack
            reStack.clear(); //clear redo as there are new updates
        } catch (BadLocationException e) {
            e.printStackTrace();
        }
    }

    public void highlightInBack() //allows frame and text pane to run without interference
    {
        SwingUtilities.invokeLater(() -> highlightKeyWords());
    }

    public void highlightKeyWords()
    {
        StyledDocument doc = txt.getStyledDocument();
        doc.setCharacterAttributes(0, doc.getLength(), defaultStyle, true);

        try{
            String all = txt.getText(0, doc.getLength());
            for(String key: keyStyles.keySet())
            {
                int pos = 0;
                while ((pos = all.indexOf(key, pos)) >= 0) 
                {
                    doc.setCharacterAttributes(pos, key.length(), keyStyles.get(key), true);
                    pos += key.length();
                }
            }
        }
        catch(Exception e)
        {
            e.printStackTrace();
        }
    }
    @Override
    public void actionPerformed(ActionEvent e) 
    {
        String event = e.getActionCommand();

        switch(event) //switch case for all jmenu items
        {
            case "New":
                if(!txt.getText().trim().equals(""))
                {
                    //show an option pane
                    int check = JOptionPane.showConfirmDialog(frame, "Do you want to save your file?", "Confirm", JOptionPane.YES_NO_CANCEL_OPTION);
                    if(check == JOptionPane.YES_OPTION) //if they choose yes, setup a jfilechooser
                    {
                        JFileChooser chooser = new JFileChooser(FileSystemView.getFileSystemView());
                        int chose = chooser.showSaveDialog(frame);

                        if(chose == JFileChooser.APPROVE_OPTION)
                        {
                            File file = new File(chooser.getSelectedFile().getAbsolutePath());
                            try
                            {  //create a file writer and write the text to a file that saves
                                BufferedWriter bw = new BufferedWriter(new FileWriter(file, false));
                                bw.write(txt.getText());
                                bw.flush();
                                bw.close();
                                txt.setText("");
                            }
                            catch(Exception ex)
                            {
                                JOptionPane.showMessageDialog(frame, ex.getMessage());
                            }
                        }
                        else
                        {
                            JOptionPane.showMessageDialog(frame, "Save Cancelled");
                            //save is cancelled
                        }
                    }
                    else if(check == JOptionPane.NO_OPTION)
                    {
                        //resets the document
                        txt.setText("");
                    }
                }
                break;

            case "Open":
                //open file chooser
                JFileChooser chooser = new JFileChooser(FileSystemView.getFileSystemView());
                int chose = chooser.showOpenDialog(frame);

                if(chose == JFileChooser.APPROVE_OPTION)
                {
                    //read file and open it onto the jframe
                    File file = new File(chooser.getSelectedFile().getAbsolutePath());
                    try
                    {  
                        BufferedReader br = new BufferedReader(new FileReader(file));
                        String strTotal = "";
                        String str = br.readLine();
                        while(str != null)
                        {
                            strTotal = strTotal + str+"\n";
                            str = br.readLine();
                        }
                        txt.setText(strTotal);
                        br.close();

                    }
                    catch(Exception ex)
                    {
                        JOptionPane.showMessageDialog(frame, ex.getMessage());
                    }
                    
                }
                break;

            case "Print": //default print
                try
                {
                    txt.print();
                } 
                catch(Exception ex)
                {
                    JOptionPane.showMessageDialog(frame, ex.getMessage());
                }
                break;
            case "Cut":
                txt.cut(); //default cut, copy, and paste
                break;

            case "Copy":
                txt.copy();
                break;

            case "Paste":
                txt.paste();
                break;

            case "FNR": //makes the find menu visible
                findMenu.setVisible(true);
                break;

            case "Search": //from the find menu, gets the string
                String searchText = tf.getText();
                if(searchText.isEmpty()) break;

                Highlighter lighter = txt.getHighlighter();
                lighter.removeAllHighlights();

                String allText = txt.getText();
                int pos = 0;
                //iterates through the jframe text and checks for all words that match
                while((pos = allText.indexOf(searchText, pos)) >= 0)
                {
                    try 
                    {//highlight words that match
                        lighter.addHighlight(pos, pos + searchText.length(), new DefaultHighlighter.DefaultHighlightPainter(Color.YELLOW));
                        pos += searchText.length();
                        dlist.insertAtBeginning(pos);
                    } 
                    catch (BadLocationException ex) 
                    {
                        ex.printStackTrace();
                    }
                }
                break;

            case "Undo":
                if(unStack.isEmpty()) break; //nothing to undo
                else if(!unStack.isFull())
                {
                    Document prev = unStack.pop(); //pops undo, sets it to document
                    try {
                        prev.addDocumentListener(this); //makes sure document listener is attached
                        reStack.push(txt.getDocument()); //pushes the same into redo
                        txt.setDocument(prev);
                        txt.setCaretPosition(txt.getDocument().getLength()); //sets caret position
                    } catch (NullPointerException ex) {
                        ex.printStackTrace();
                    }
                }
                else unStack.clear();
                txt.getHighlighter().removeAllHighlights();
                break;

            case "<":
                txt.setCaretPosition(dlist.head.prev.value); //iterates through doubly circular linked list for cursor positions
                dlist.head = dlist.head.prev;
                break;

            case ">":
                txt.setCaretPosition(dlist.head.next.value);//iterates through doubly circular linked list for cursor positions
                dlist.head = dlist.head.next;
                break;

            case "Redo":
                if(reStack.isEmpty()) break; //if nothing to redo
                else if(!reStack.isFull())
                {
                    Document prev = reStack.pop(); //pops out of redo
                    try {
                        unStack.push(txt.getDocument()); //pushes to undo
                        txt.setDocument(prev);
                        txt.setCaretPosition(txt.getDocument().getLength()); //sets caret position
                    } catch (NullPointerException ex) {
                        ex.printStackTrace();
                    }
                }
                break;

            //fonts and font sizes
            case "Arial":
                setFont("Arial");
                break;
            
            case "Times New Roman":
                setFont("Times New Roman");
                break;

            case "8":
                createFont(8);
                break;

            case "16":
                createFont(16);
                break;

            case "10":
                createFont(10);
                break;

            case "12":
                createFont(12);
                break;

            case "24":
                createFont(24);
                break;

            case "48":
                createFont(48);
                break;

            case "Code Mode: OFF":
                codeMode = true; //sets code mode on to trigger highlight keywords
                txt.setBackground(Color.BLACK); //changes back and foreground
                txt.setForeground(Color.WHITE);
                mode.setText("Code Mode: ON");
                break;
            
            case "Code Mode: ON":
                codeMode = false; //sets code mode off to not trigger highlight keywords
                txt.setBackground(Color.WHITE); //changes back and foreground
                txt.setForeground(Color.BLACK);
                txt.getStyledDocument().setCharacterAttributes(0, txt.getStyledDocument().getLength(), defaultStyle, true); //resets all highlighted keywords
                mode.setText("Code Mode: OFF");
                break;
            default:
                break;
        }
    }

    public static void main(String[] args) {
        TextEditor e = new TextEditor();
    }

}
